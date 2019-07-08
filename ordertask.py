#!/usr/bin/env python3
#    Copyright (C) 2019 by Bitonic B.V.
#
#    This file is part of the BL4P Client.
#
#    The BL4P Client is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    The BL4P Client is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with the BL4P Client. If not, see <http://www.gnu.org/licenses/>.

import asyncio
import hashlib

from bl4p_api import offer
from bl4p_api import offer_pb2
from bl4p_api.offer import Offer

from log import log, logException
import messages
import order
from order import BuyOrder, SellOrder
import settings
from storage import StoredObject



def getMinConditionValue(offer1, offer2, condition):
	return max(
		offer1.getConditionMin(condition),
		offer2.getConditionMin(condition)
		)


def getMaxConditionValue(offer1, offer2, condition):
	return min(
		offer1.getConditionMax(condition),
		offer2.getConditionMax(condition)
		)


sha256 = lambda preimage: hashlib.sha256(preimage).digest()



#Transaction status
'''
State transitions:

Seller market taker:
initial -> locked -> received_preimage -> finished
                  -> canceled

Buyer market maker:
initial -> finished
        -> canceled
'''
STATUS_INITIAL = 0
STATUS_LOCKED = 1
STATUS_RECEIVED_PREIMAGE = 2
STATUS_FINISHED = 3
STATUS_CANCELED = 4



class BuyTransaction(StoredObject):
	@staticmethod
	def create(storage, buyOrder, fiatAmount, cryptoAmount, paymentHash):
		return StoredObject.create(
			storage, 'buyTransactions',

			buyOrder = buyOrder,

			status = STATUS_INITIAL,

			fiatAmount   = fiatAmount,
			cryptoAmount = cryptoAmount,

			paymentHash    = paymentHash,
			paymentPreimage= None,
			)


	def __init__(self, storage, ID):
		StoredObject.__init__(self, storage, 'buyTransactions', ID)



class SellTransaction(StoredObject):
	@staticmethod
	def create(storage, sellOrder, counterOffer, senderFiatAmount, maxSenderCryptoAmount, receiverCryptoAmount, senderTimeoutDelta, lockedTimeoutDelta, CLTVExpiryDelta):
		return StoredObject.create(
			storage, 'sellTransactions',

			sellOrder  = sellOrder,
			counterOffer = counterOffer,

			status = STATUS_INITIAL,

			senderFiatAmount   = senderFiatAmount, #amount of sender of fiat
			receiverFiatAmount = None,             #amount of receiver of fiat

			maxSenderCryptoAmount = maxSenderCryptoAmount,
			senderCryptoAmount    = None,                  #amount of sender of crypto
			receiverCryptoAmount  = receiverCryptoAmount,  #amount of sender of crypto

			senderTimeoutDelta = senderTimeoutDelta,
			lockedTimeoutDelta = lockedTimeoutDelta,
			CLTVExpiryDelta    = CLTVExpiryDelta,

			paymentHash     = None,
			paymentPreimage = None,
			)


	def __init__(self, storage, ID):
		StoredObject.__init__(self, storage, 'sellTransactions', ID)



class CounterOffer(StoredObject):
	@staticmethod
	def create(storage, counterOffer):
		return StoredObject.create(
			storage, 'counterOffers',
			blob = counterOffer.toPB2().SerializeToString(),
			)


	def __init__(self, storage, ID):
		StoredObject.__init__(self, storage, 'counterOffers', ID)
		counterOffer = offer_pb2.Offer()
		counterOffer.ParseFromString(self.blob)
		self.counterOffer = Offer.fromPB2(counterOffer)



class UnexpectedResult(Exception):
	pass



class BL4PError(Exception):
	pass



class OrderTask:
	def __init__(self, client, storage, order):
		self.client = client
		self.storage = storage
		self.callResult = None
		self.expectedCallResultType = None

		self.order = order
		self.counterOffer = None
		self.transaction = None


	def startup(self):
		self.task = asyncio.ensure_future(self.doTrading())


	async def shutdown(self):
		self.task.cancel()
		await self.task


	async def waitFinished(self):
		await self.task


	def setCallResult(self, result):
		if self.callResult is None:
			raise UnexpectedResult(
				'Received a call result while no call was going on: ' + \
				str(result)
				)
		if not isinstance(result, (self.expectedCallResultType, messages.BL4PError)):
			raise UnexpectedResult(
				'Received a call result of unexpected type: ' + \
				str(result)
				)
		self.callResult.set_result(result)


	async def doTrading(self):
		try:
			if isinstance(self.order, BuyOrder):
				await self.continueBuyTransaction()
				await self.publishOffer()
				while self.order.amount > 0:
					await self.waitForIncomingTransaction()
					log('Remaining in buy order: ' + \
						str(self.order.amount))
				log('Finished with buy order')
			elif isinstance(self.order, SellOrder):
				await self.continueSellTransaction()
				while self.order.amount > 0:
					await self.doOfferSearch()
					log('Remaining in sell order: ' + \
						str(self.order.amount))
				log('Finished with sell order')
			else:
				raise Exception('Unsupported order type - cannot use it in trade')

			self.order.update(status=order.STATUS_COMPLETED)

		except asyncio.CancelledError:
			pass #We're cancelled, so just quit the function
		except:
			log('Exception in order task:')
			logException()

		self.client.backend.handleOrderTaskFinished(self.order.ID)


	async def doOfferSearch(self):
		'''
		Keeps searching for matching offers until it finds one.
		Then, it performs a single transaction based on the found offer.
		'''

		while True:
			queryResult = await self.call(messages.BL4PFindOffers(
				localOrderID=self.order.ID,

				query=self.order
				),
				messages.BL4PFindOffersResult)

			if queryResult.offers: #found a matching offer
				log('Found offers - starting a transaction')
				#TODO: filter on sensibility (e.g. max >= min for all conditions)
				#TODO: check if offers actually match
				#TODO: filter counterOffers on acceptability
				#TODO: sort counterOffers (e.g. on exchange rate)

				#Start trade on the first in the list
				self.counterOffer = queryResult.offers[0]
				await self.doTransaction()
				return

			if self.order.remoteOfferID is None:
				log('Found no offers - making our own')
				await self.publishOffer()

			await asyncio.sleep(1)


	async def publishOffer(self):
		result = await self.call(messages.BL4PAddOffer(
			localOrderID=self.order.ID,

			offer=self.order
			),
			messages.BL4PAddOfferResult)
		remoteID = result.ID
		self.order.remoteOfferID = remoteID
		log('Local ID %d gets remote ID %s' % (self.order.ID, remoteID))


	########################################################################
	# Seller side
	########################################################################

	async def continueSellTransaction(self):
		cursor = self.storage.execute(
			'SELECT ID from sellTransactions WHERE sellOrder = ? AND status != ? AND status != ?',
			[self.order.ID, STATUS_FINISHED, STATUS_CANCELED]
			)
		IDs = [row[0] for row in cursor]
		assert len(IDs) < 2 #TODO: properly report database inconsistency error
		if len(IDs) == 0:
			return #no transaction needs to be continued
		ID = IDs[0]

		log('Found an unfinished transaction with ID %d - loading it' % ID)

		self.transaction = SellTransaction(self.storage, ID)
		storedCounterOffer = CounterOffer(self.storage, self.transaction.counterOffer)
		self.counterOffer = storedCounterOffer.counterOffer

		if self.transaction.status == STATUS_INITIAL:
			await self.startTransactionOnBL4P()
		elif self.transaction.status == STATUS_LOCKED:
			await self.doTransactionOnLightning()
		elif self.transaction.status == STATUS_RECEIVED_PREIMAGE:
			await self.receiveFiatFunds()
		else:
			#TODO: properly report database inconsistency error
			raise Exception('Invalid transaction status value in unfinished transaction')


	async def doTransaction(self):
		assert isinstance(self.order, SellOrder) #TODO: enable buyer-initiated trade once supported

		log('Doing trade for local order ID' + str(self.order.ID))
		log('  local order: ' + str(self.order))
		log('  counter offer: ' + str(self.counterOffer))

		#Choose the largest fiat amount accepted by both
		fiatAmountDivisor = settings.fiatDivisor
		senderFiatAmount = min(
			fiatAmountDivisor * self.order.ask.max_amount // self.order.ask.max_amount_divisor,
			fiatAmountDivisor * self.counterOffer.bid.max_amount // self.counterOffer.bid.max_amount_divisor
			)
		assert senderFiatAmount > 0
		log('senderFiatAmount = ' + str(senderFiatAmount))

		#Minimum: this is what the other wants
		#btc = eur * (btc / eur)
		#    = eur * (ask / bid)
		#    = eur * (ask / ask_divisor) / (bid / bid_divisor)
		#    = (eur * ask * bid_divisor) / (bid * ask_divisor)
		#Implementation note:
		#The correctness of this code might depend on Python's unlimited size integers.
		cryptoAmountDivisor = settings.cryptoDivisor
		receiverCryptoAmount = \
			(cryptoAmountDivisor * senderFiatAmount  * self.counterOffer.ask.max_amount         * self.counterOffer.bid.max_amount_divisor) // \
			(                      fiatAmountDivisor * self.counterOffer.ask.max_amount_divisor * self.counterOffer.bid.max_amount)
		log('receiverCryptoAmount = ' + str(receiverCryptoAmount))
		assert receiverCryptoAmount >= 0
		#Maximum: this is what we are prepared to pay
		maxSenderCryptoAmount = \
			(cryptoAmountDivisor * senderFiatAmount  * self.order.bid.max_amount         * self.order.ask.max_amount_divisor) // \
			(                      fiatAmountDivisor * self.order.bid.max_amount_divisor * self.order.ask.max_amount)
		log('maxSenderCryptoAmount = ' + str(maxSenderCryptoAmount))
		assert maxSenderCryptoAmount >= receiverCryptoAmount

		#Choose the sender timeout limit as small as possible
		sender_timeout_delta_ms = getMinConditionValue(
			self.order, self.counterOffer,
			offer.Condition.SENDER_TIMEOUT
			)

		#Choose the locked timeout limit as large as possible
		locked_timeout_delta_s = getMaxConditionValue(
			self.order, self.counterOffer,
			offer.Condition.LOCKED_TIMEOUT
			)

		#Choose the CLTV expiry delta as small as possible
		CLTV_expiry_delta = getMinConditionValue(
			self.order, self.counterOffer,
			offer.Condition.CLTV_EXPIRY_DELTA
			)

		#TODO: check if it's already in the database
		counterOfferID = CounterOffer.create(self.storage, self.counterOffer)

		sellTransactionID = SellTransaction.create(self.storage,
			sellOrder    = self.order.ID,
			counterOffer = counterOfferID,

			senderFiatAmount   = senderFiatAmount,

			maxSenderCryptoAmount = maxSenderCryptoAmount,
			receiverCryptoAmount  = receiverCryptoAmount,

			senderTimeoutDelta = sender_timeout_delta_ms,
			lockedTimeoutDelta = locked_timeout_delta_s,
			CLTVExpiryDelta    = CLTV_expiry_delta,
			)
		self.transaction = SellTransaction(self.storage, sellTransactionID)

		await self.startTransactionOnBL4P()


	async def startTransactionOnBL4P(self):
		#Create transaction on the exchange:
		startResult = await self.call(messages.BL4PStart(
			localOrderID = self.order.ID,

			amount = self.transaction.senderFiatAmount,
			sender_timeout_delta_ms = self.transaction.senderTimeoutDelta,
			locked_timeout_delta_s = self.transaction.lockedTimeoutDelta,
			receiver_pays_fee = True
			),
			messages.BL4PStartResult)

		assert startResult.senderAmount == self.transaction.senderFiatAmount
		#TODO: check that we're not paying too much fees to BL4P

		self.transaction.update(
			receiverFiatAmount = startResult.receiverAmount,
			paymentHash = startResult.paymentHash,
			status = STATUS_LOCKED,
			)

		await self.doTransactionOnLightning()


	async def doTransactionOnLightning(self):
		#Send out over Lightning:
		lightningResult = await self.call(messages.LNPay(
			localOrderID = self.order.ID,

			destinationNodeID     = self.counterOffer.address,
			paymentHash           = self.transaction.paymentHash,
			recipientCryptoAmount = self.transaction.receiverCryptoAmount,
			maxSenderCryptoAmount = self.transaction.maxSenderCryptoAmount,
			minCLTVExpiryDelta    = self.transaction.CLTVExpiryDelta,
			fiatAmount            = self.transaction.senderFiatAmount,
			offerID               = self.counterOffer.ID,
			),
			messages.LNPayResult)

		if lightningResult.paymentPreimage is None:
			#LN transaction failed, so revert everything we got so far
			log('Outgoing Lightning transaction failed; canceling the transaction')
			await self.cancelIncomingFiatFunds()
			return

		assert sha256(lightningResult.paymentPreimage) == self.transaction.paymentHash
		log('We got the preimage from the LN payment')

		self.transaction.update(
			senderCryptoAmount = lightningResult.senderCryptoAmount,
			paymentPreimage = lightningResult.paymentPreimage,
			status = STATUS_RECEIVED_PREIMAGE,
			)
		self.order.setAmount(self.order.amount - self.transaction.senderCryptoAmount)

		await self.receiveFiatFunds()


	async def receiveFiatFunds(self):
		receiveResult = await self.call(messages.BL4PReceive(
			localOrderID=self.order.ID,

			paymentPreimage=self.transaction.paymentPreimage,
			),
			messages.BL4PReceiveResult)

		self.transaction.update(
			status = STATUS_FINISHED,
			)
		self.transaction = None

		log('Sell transaction is finished')
		await self.updateOrderAfterTransaction()


	async def cancelIncomingFiatFunds(self):
		await self.call(messages.BL4PCancelStart(
			localOrderID=self.order.ID,

			paymentHash=self.transaction.paymentHash,
			),
			messages.BL4PCancelStartResult)

		self.transaction.update(
			status = STATUS_CANCELED,
			)
		self.transaction = None

		log('Sell transaction is canceled')
		#TODO: do we need to call updateOrderAfterTransaction()?


	########################################################################
	# Buyer side
	########################################################################

	async def continueBuyTransaction(self):
		cursor = self.storage.execute(
			'SELECT ID from buyTransactions WHERE buyOrder = ? AND status != ? AND status != ?',
			[self.order.ID, STATUS_FINISHED, STATUS_CANCELED]
			)
		IDs = [row[0] for row in cursor]
		assert len(IDs) < 2 #TODO: properly report database inconsistency error
		if len(IDs) == 0:
			return #no transaction needs to be continued
		ID = IDs[0]

		log('Found an unfinished transaction with ID %d - loading it' % ID)

		self.transaction = BuyTransaction(self.storage, ID)

		if self.transaction.status == STATUS_INITIAL:
			await self.sendFundsOnBL4P()
		else:
			#TODO: properly report database inconsistency error
			raise Exception('Invalid transaction status value in unfinished transaction')


	async def waitForIncomingTransaction(self):
		message = await self.waitForIncomingMessage(messages.LNIncoming)

		#TODO: check if this is a new notification for an already
		#ongoing tx.
		#In that case, simply send back the payment preimage again.

		#TODO: proper handling of failing this condition:
		assert self.order.amount > 0

		#TODO: check if lntx conforms to our order

		log('Received incoming Lightning transaction')

		#Check if remaining order size is sufficient:
		assert message.fiatAmount <= self.order.amount

		buyTransactionID = BuyTransaction.create(self.storage,
			buyOrder = self.order.ID,

			fiatAmount   = message.fiatAmount,
			cryptoAmount = message.cryptoAmount,

			paymentHash = message.paymentHash,
			)
		self.order.setAmount(self.order.amount - message.fiatAmount)
		self.transaction = BuyTransaction(self.storage, buyTransactionID)

		await self.sendFundsOnBL4P()


	async def sendFundsOnBL4P(self):
		try:
			#Lock fiat funds:
			sendResult = await self.call(messages.BL4PSend(
				localOrderID = self.order.ID,

				amount      = self.transaction.fiatAmount,
				paymentHash = self.transaction.paymentHash,
				),
				messages.BL4PSendResult)
		except BL4PError:
			log('Error received from BL4P - transaction canceled')
			self.order.setAmount(self.order.amount + self.transaction.fiatAmount)
			self.transaction.update(
				status = STATUS_CANCELED,
				)
			await self.cancelTransactionOnLightning()
			return

		#TODO: what if this asserion fails?
		assert sha256(sendResult.paymentPreimage) == self.transaction.paymentHash
		log('We got the preimage from BL4P')

		self.transaction.update(
			paymentPreimage = sendResult.paymentPreimage,
			status = STATUS_FINISHED,
			)

		await self.finishTransactionOnLightning()


	async def finishTransactionOnLightning(self):
		#Receive crypto funds
		self.client.handleOutgoingMessage(messages.LNFinish(
			paymentHash=self.transaction.paymentHash,
			paymentPreimage=self.transaction.paymentPreimage,
			))
		self.transaction = None

		log('Buy transaction is finished')
		await self.updateOrderAfterTransaction()


	async def cancelTransactionOnLightning(self):
		self.client.handleOutgoingMessage(messages.LNFail(
			paymentHash=self.transaction.paymentHash,
			))
		self.transaction = None

		log('Buy transaction is canceled')

		#TODO: is this really needed?
		await self.updateOrderAfterTransaction()


	########################################################################
	# Generic
	########################################################################

	async def updateOrderAfterTransaction(self):
		if self.order.remoteOfferID is not None:
			#Remove offer from the market
			log('Removing old offer from the market')
			await self.call(messages.BL4PRemoveOffer(
				localOrderID=self.order.ID,

				offerID=self.order.remoteOfferID,
				),
				messages.BL4PRemoveOfferResult)

			#Re-add offer to the market
			if self.order.amount > 0:
				log('Re-adding the offer to the market')
				await self.publishOffer()


	async def call(self, message, expectedResultType):
		self.client.handleOutgoingMessage(message)
		return await self.waitForIncomingMessage(expectedResultType)


	async def waitForIncomingMessage(self, expectedResultType):
		assert self.callResult is None
		self.callResult = asyncio.Future()
		self.expectedCallResultType = expectedResultType
		await self.callResult
		ret = self.callResult.result()

		#Special case for BL4P exceptions
		if isinstance(ret, messages.BL4PError):
			self.callResult = None
			self.expectedCallResultType = None
			raise BL4PError()

		assert isinstance(ret, expectedResultType)
		self.callResult = None
		self.expectedCallResultType = None
		return ret

