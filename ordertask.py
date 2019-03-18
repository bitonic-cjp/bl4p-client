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

from log import log, logException
import messages
import order
from order import BuyOrder, SellOrder
import settings
from simplestruct import Struct



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



#status
'''
State transitions:

Seller market taker:
initial -> locked -> received_preimage -> finished

Buyer market maker:
locked -> finished
'''
STATUS_INITIAL = 0
STATUS_LOCKED = 1
STATUS_RECEIVED_PREIMAGE = 2
STATUS_FINISHED = 3



class BuyTransaction(Struct):
	status = None
	localOrderID = None

	fiatAmount = None
	cryptoAmount = None

	paymentHash = None
	paymentPreimage = None



class SellTransaction(Struct):
	status = None
	localOrderID = None
	counterOffer = None

	fiatAmount = None #Nominal fiat amount (without fees)
	minCryptoAmount = None
	maxCryptoAmount = None
	senderAmount = None   #Fiat amount of sender of fiat
	receiverAmount = None #Fiat amount of receiver of fiat

	sender_timeout_delta_ms = None
	locked_timeout_delta_s = None
	CLTV_expiry_delta = None

	paymentHash = None
	paymentPreimage = None



class OrderTask:
	def __init__(self, client, order):
		self.client = client
		self.callResult = None

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
		self.callResult.set_result(result)


	async def doTrading(self):
		try:
			if isinstance(self.order, BuyOrder):
				await self.publishOffer()
				await self.waitForIncomingTransactions()
			elif isinstance(self.order, SellOrder):
				await self.doOfferSearch()
			else:
				raise Exception('Unsupported order type - cannot use it in trade')
		except asyncio.CancelledError:
			pass #We're cancelled, so just quit the function
		except:
			log('Exception in order task:')
			logException()


	async def doOfferSearch(self):
		while True: #TODO: quit once the order is finished
			queryResult = await self.call(messages.BL4PFindOffers(
				localOrderID=self.order.ID,

				query=self.order
				))

			if queryResult.offers: #found a matching offer
				log('Found offers - starting a transaction')
				#TODO: filter on sensibility (e.g. max >= min for all conditions)
				#TODO: check if offers actually match
				#TODO: filter counterOffers on acceptability
				#TODO: sort counterOffers (e.g. on exchange rate)

				#Start trade on the first in the list
				self.counterOffer = queryResult.offers[0]
				await self.doTransaction()
				#TODO: maybe continue if the order is not yet complete
				return

			if self.order.remoteOfferID is None:
				log('Found no offers - making our own')
				await self.publishOffer()

			await asyncio.sleep(1)


	async def publishOffer(self):
		result = await self.call(messages.BL4PAddOffer(
			localOrderID=self.order.ID,

			offer=self.order
			))
		remoteID = result.ID
		self.order.remoteOfferID = remoteID
		self.client.backend.updateOrder(self.order)
		log('Local ID %d gets remote ID %s' % (self.order.ID, remoteID))


	########################################################################
	# Seller side
	########################################################################

	async def doTransaction(self):
		assert isinstance(self.order, SellOrder) #TODO: enable buyer-initiated trade once supported

		log('Doing trade for local order ID' + str(self.order.ID))
		log('  local order: ' + str(self.order))
		log('  counter offer: ' + str(self.counterOffer))

		#Choose the largest fiat amount accepted by both
		fiatAmountDivisor = settings.fiatDivisor
		fiatAmount = min(
			fiatAmountDivisor * self.order.ask.max_amount // self.order.ask.max_amount_divisor,
			fiatAmountDivisor * self.counterOffer.bid.max_amount // self.counterOffer.bid.max_amount_divisor
			)
		assert fiatAmount > 0

		#Minimum: this is what the other wants
		#btc = eur * (btc / eur)
		#    = eur * (ask / bid)
		#    = eur * (ask / ask_divisor) / (bid / bid_divisor)
		#    = (eur * ask * bid_divisor) / (bid * ask_divisor)
		#Implementation note:
		#The correctness of this code might depend on Python's unlimited size integers.
		cryptoAmountDivisor = settings.cryptoDivisor
		minCryptoAmount = \
			(cryptoAmountDivisor * fiatAmount        * self.counterOffer.ask.max_amount         * self.counterOffer.bid.max_amount_divisor) // \
			(                      fiatAmountDivisor * self.counterOffer.ask.max_amount_divisor * self.counterOffer.bid.max_amount)
		#Maximum: this is what we are prepared to pay
		maxCryptoAmount = \
			(cryptoAmountDivisor * fiatAmount        * self.order.bid.max_amount         * self.order.ask.max_amount_divisor) // \
			(                      fiatAmountDivisor * self.order.bid.max_amount_divisor * self.order.ask.max_amount)
		assert minCryptoAmount >= 0
		assert maxCryptoAmount >= minCryptoAmount

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

		self.transaction = SellTransaction(
			status = STATUS_INITIAL,
			localOrderID = self.order.ID,
			counterOffer = self.counterOffer,
			fiatAmount = fiatAmount,
			minCryptoAmount = minCryptoAmount,
			maxCryptoAmount = maxCryptoAmount,
			sender_timeout_delta_ms = sender_timeout_delta_ms,
			locked_timeout_delta_s = locked_timeout_delta_s,
			CLTV_expiry_delta = CLTV_expiry_delta,
			)

		self.order.status = order.STATUS_TRADING
		self.client.backend.updateOrder(self.order)

		await self.startTransactionOnBL4P()


	async def startTransactionOnBL4P(self):
		#Create transaction on the exchange:
		startResult = await self.call(messages.BL4PStart(
			localOrderID = self.order.ID,

			amount = self.transaction.fiatAmount,
			sender_timeout_delta_ms = self.transaction.sender_timeout_delta_ms,
			locked_timeout_delta_s = self.transaction.locked_timeout_delta_s,
			receiver_pays_fee = True
			))

		assert startResult.senderAmount == self.transaction.fiatAmount
		#TODO: check that we're not paying too much fees to BL4P

		self.transaction.senderAmount = startResult.senderAmount     #Sender of *fiat*
		self.transaction.receiverAmount = startResult.receiverAmount #Receiver of *fiat*
		self.transaction.paymentHash = startResult.paymentHash
		self.transaction.status = STATUS_LOCKED

		await self.doTransactionOnLightning()


	async def doTransactionOnLightning(self):
		#Send out over Lightning:
		lightningResult = await self.call(messages.LNPay(
			localOrderID = self.order.ID,

			destinationNodeID     = self.transaction.counterOffer.address,
			paymentHash           = self.transaction.paymentHash,
			recipientCryptoAmount = self.transaction.minCryptoAmount,
			maxSenderCryptoAmount = self.transaction.maxCryptoAmount,
			minCLTVExpiryDelta    = self.transaction.CLTV_expiry_delta,
			fiatAmount            = self.transaction.fiatAmount,
			offerID               = self.transaction.counterOffer.ID,
			))

		assert sha256(lightningResult.paymentPreimage) == self.transaction.paymentHash
		log('We got the preimage from the LN payment')

		self.transaction.paymentPreimage = lightningResult.paymentPreimage
		self.transaction.status = STATUS_RECEIVED_PREIMAGE

		await self.receiveFiatFunds()


	async def receiveFiatFunds(self):
		receiveResult = await self.call(messages.BL4PReceive(
			localOrderID=self.order.ID,

			paymentPreimage=self.transaction.paymentPreimage,
			))

		self.transaction.status = STATUS_FINISHED
		log('Transaction is finished')
		#TODO: clean up everything


	########################################################################
	# Buyer side
	########################################################################

	async def waitForIncomingTransactions(self):
		self.callResult = asyncio.Future()
		await self.callResult
		message = self.callResult.result()

		assert isinstance(message, messages.LNIncoming)

		#TODO: check if this is a new notification for an already
		#ongoing tx.
		#In that case, simply send back the payment preimage again.

		#TODO: proper handling of failing this condition:
		assert self.order.status == order.STATUS_IDLE

		#TODO: check if lntx conforms to our order
		#TODO: check if remaining order size is sufficient

		self.transaction = BuyTransaction(
			status = STATUS_LOCKED,
			localOrderID = self.order.ID,
			cryptoAmount = message.cryptoAmount,
			fiatAmount = message.fiatAmount,
			paymentHash = message.paymentHash,
			)

		log('Received incoming Lightning transaction')

		self.order.status = order.STATUS_TRADING
		self.client.backend.updateOrder(self.order)

		await self.sendFundsOnBL4P()


	async def sendFundsOnBL4P(self):
		#Lock fiat funds:
		sendResult = await self.call(messages.BL4PSend(
			localOrderID = self.order.ID,

			amount      = self.transaction.fiatAmount,
			paymentHash = self.transaction.paymentHash,
			))

		assert sha256(sendResult.paymentPreimage) == self.transaction.paymentHash
		log('We got the preimage from BL4P')

		self.transaction.paymentPreimage = sendResult.paymentPreimage
		self.transaction.status = STATUS_FINISHED

		await self.finishTransactionOnLightning()


	async def finishTransactionOnLightning(self):
		#Receive crypto funds
		self.client.handleOutgoingMessage(messages.LNFinish(
			paymentHash=self.transaction.paymentHash,
			paymentPreimage=self.transaction.paymentPreimage,
			))

		#TODO: clean up everything



	async def call(self, message):
		self.client.handleOutgoingMessage(message)
		self.callResult = asyncio.Future()
		await self.callResult
		return self.callResult.result()

