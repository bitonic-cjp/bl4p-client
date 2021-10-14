#!/usr/bin/env python3
#    Copyright (C) 2019-2021 by Bitonic B.V.
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
import copy
import hashlib
import logging
from typing import TYPE_CHECKING, cast, Any, Awaitable, Callable, Dict, List, Optional, Type, Union

from bl4p_api import offer
from bl4p_api import offer_pb2
from bl4p_api.offer import Offer, Asset

if TYPE_CHECKING:
	import bl4p_plugin #pragma: nocover

import messages
from order import BuyOrder, SellOrder, Order
import order
import settings
from storage import StoredObject, Storage, Cursor



def getMinConditionValue(offer1: offer.Offer, offer2: offer.Offer, condition: int) -> int:
	return max(
		offer1.getConditionMin(condition),
		offer2.getConditionMin(condition)
		)


def getMaxConditionValue(offer1: offer.Offer, offer2: offer.Offer, condition: int) -> int:
	return min(
		offer1.getConditionMax(condition),
		offer2.getConditionMax(condition)
		)


sha256 = lambda preimage: hashlib.sha256(preimage).digest()


def formatCryptoAmount(amount: int) -> str:
	#We could use decimal.Decimal, but it gives scientific notation for very small values.
	#Instead, do this:
	divisor = settings.cryptoDivisor #type: int
	divWidth = len(str(divisor)) #type: int
	return '{integer}.{fraction:0{width}d}'.format(
		integer = amount // divisor,
		fraction = amount % divisor,
		width = divWidth-1)



#Transaction status
'''
State transitions:

Seller market taker:
initial -> started -> locked -> received_preimage -> finished
                   -> canceled

Buyer market maker:
initial -> finished
        -> canceled
'''
TX_STATUS_INITIAL           = 0 #type: int
TX_STATUS_STARTED           = 1 #type: int
TX_STATUS_LOCKED            = 2 #type: int
TX_STATUS_RECEIVED_PREIMAGE = 3 #type: int
TX_STATUS_FINISHED          = 4 #type: int
TX_STATUS_CANCELED          = 5 #type: int

TxStatus2str = \
{
TX_STATUS_INITIAL           : 'initial',
TX_STATUS_STARTED           : 'started',
TX_STATUS_LOCKED            : 'locked',
TX_STATUS_RECEIVED_PREIMAGE : 'received preimage',
TX_STATUS_FINISHED          : 'finished',
TX_STATUS_CANCELED          : 'canceled',
}



class BuyTransaction(StoredObject):
	#This initialization is just to inform Mypy about data types.
	#TODO: find a way to make sure Storage respects these types
	buyOrder        = None #type: int
	status          = None #type: int
	fiatAmount      = None #type: int
	cryptoAmount    = None #type: int
	paymentHash     = None #type: bytes
	paymentPreimage = None #type: bytes

	@staticmethod
	def create(storage: Storage,
		buyOrder: int, fiatAmount: int, cryptoAmount: int, paymentHash: bytes
		) -> int:

		return StoredObject.createStoredObject(
			storage, 'buyTransactions',

			buyOrder = buyOrder,

			status = TX_STATUS_INITIAL,

			fiatAmount   = fiatAmount,
			cryptoAmount = cryptoAmount,

			paymentHash    = paymentHash,
			paymentPreimage= None,
			)


	def __init__(self, storage: Storage, ID: int) -> None:
		StoredObject.__init__(self, storage, 'buyTransactions', ID)


	def getListInfo(self) -> Dict[str, Any]:
		'Return information intended for the list RPC call'

		return \
		{
		'status'      : TxStatus2str[self.status],
		'fiatAmount'  : self.fiatAmount,
		'cryptoAmount': self.cryptoAmount,
		}



class SellTransaction(StoredObject):
	#This initialization is just to inform Mypy about data types.
	#TODO: find a way to make sure Storage respects these types
	sellOrder          = None #type: int
	counterOffer       = None #type: int
	status             = None #type: int
	buyerFiatAmount    = None #type: int
	sellerFiatAmount   = None #type: int
	buyerCryptoAmount  = None #type: int
	sellerCryptoAmount = None #type: int
	senderTimeoutDelta = None #type: int
	lockedTimeoutDelta = None #type: int
	CLTVExpiryDelta    = None #type: int
	paymentHash        = None #type: bytes
	paymentPreimage    = None #type: bytes

	@staticmethod
	def create(storage: Storage,
		sellOrder: int, counterOffer: int, buyerFiatAmount: int, buyerCryptoAmount: int, senderTimeoutDelta: int, lockedTimeoutDelta: int, CLTVExpiryDelta: int
		) -> int:

		return StoredObject.createStoredObject(
			storage, 'sellTransactions',

			sellOrder  = sellOrder,
			counterOffer = counterOffer,

			status = TX_STATUS_INITIAL,

			buyerFiatAmount  = buyerFiatAmount, #buyer-side fiat amount
			sellerFiatAmount = None,            #seller-side fiat amount

			buyerCryptoAmount  = buyerCryptoAmount,  #buyer-side crypto amount
			sellerCryptoAmount = None,               #seller-side crypto amount

			senderTimeoutDelta = senderTimeoutDelta,
			lockedTimeoutDelta = lockedTimeoutDelta,
			CLTVExpiryDelta    = CLTVExpiryDelta,

			paymentHash     = None,
			paymentPreimage = None,
			)


	def __init__(self, storage: Storage, ID: int) -> None:
		StoredObject.__init__(self, storage, 'sellTransactions', ID)


	def getListInfo(self) -> Dict[str, Any]:
		'Return information intended for the list RPC call'

		return \
		{
		'status'            : TxStatus2str[self.status],
		'buyerFiatAmount'   : self.buyerFiatAmount,
		'sellerFiatAmount'  : self.sellerFiatAmount,
		'buyerCryptoAmount' : self.buyerCryptoAmount,
		'sellerCryptoAmount': self.sellerCryptoAmount,
		}



class CounterOffer(StoredObject):
	#This initialization is just to inform Mypy about data types.
	#TODO: find a way to make sure Storage respects these types
	blob = None #type: bytes

	@staticmethod
	def create(storage: Storage, counterOffer: offer.Offer) -> int:
		return StoredObject.createStoredObject(
			storage, 'counterOffers',
			blob = counterOffer.toPB2().SerializeToString(),
			)


	def __init__(self, storage: Storage, ID: int) -> None:
		StoredObject.__init__(self, storage, 'counterOffers', ID)
		counterOffer = offer_pb2.Offer()
		counterOffer.ParseFromString(self.blob)
		self.counterOffer = Offer.fromPB2(counterOffer)



class UnexpectedResult(Exception):
	pass



class BL4PError(Exception):
	pass



class OrderTask:
	task = None #type: asyncio.Future

	def __init__(self, client: 'bl4p_plugin.BL4PClient', s: Storage, o: Order) -> None:
		self.client = client #type: bl4p_plugin.BL4PClient
		self.storage = s #type: Storage
		self.callResult = None #type: Optional[asyncio.Future]
		self.expectedCallResultType = None #type: Optional[Type]

		self.order = o #type: Order
		self.counterOffer = None #type: Optional[offer.Offer]
		self.transaction = None #type: Optional[Union[BuyTransaction, SellTransaction]]


	def startup(self) -> None:
		self.task = asyncio.ensure_future(self.doTrading()) #type: ignore #mypy has weird ideas about ensure_future


	async def shutdown(self) -> None:
		#Note: calling this method can be a bit risky, since it awaits for the
		#task to finish.
		#After receiving the CancelledError exception, the task still performs
		#one last action, which involves an RPC call to the BL4P server; the
		#result of this call is awaited in the task.
		#If this result doesn't arrive (e.g. because the task responsible for
		#delivering the message is awaiting this method), this method won't
		#finish.
		#In the way the client code works, this should not be a problem, since
		#shutdown is typically called by a task started in bl4p_plugin.py,
		#while the RPC result is delivered by a different task started in
		#asynclient.py.
		self.task.cancel()
		await self.task


	async def waitFinished(self) -> None:
		await self.task


	def cancel(self) -> None:
		if self.transaction is None:
			self.order.update(status=order.ORDER_STATUS_CANCELED)
			self.task.cancel()
		else:
			#TODO: cancel ongoing transaction if possible.
			#For now, just let an ongoing transaction complete, and then cancel
			#the order.
			self.order.update(status=order.ORDER_STATUS_CANCEL_REQUESTED)


	def getListInfo(self)-> Dict[str, Any]:
		'Return information intended for the list RPC call'

		orderStatus = \
		{
		order.ORDER_STATUS_ACTIVE          : 'active',
		order.ORDER_STATUS_COMPLETED       : 'completed',
		order.ORDER_STATUS_CANCEL_REQUESTED: 'cancel requested',
		order.ORDER_STATUS_CANCELED        : 'canceled',
		}[self.order.status]

		ret = \
		{
		'ID': self.order.ID,
		'status': orderStatus,
		'limitRate': self.order.limitRate,
		'amount': self.order.amount,
		}

		if self.transaction is not None:
			ret['transaction'] = self.transaction.getListInfo()

		return ret


	def setCallResult(self, result: messages.AnyMessage) -> None:
		if self.callResult is None or self.expectedCallResultType is None:
			raise UnexpectedResult(
				'Received a call result while no call was going on: ' + \
				str(result)
				)
		if not isinstance(result, (self.expectedCallResultType, messages.BL4PError)):
			raise UnexpectedResult(
				'Received a call result of unexpected type: %s: expected type %s' % \
				(str(result), str(self.expectedCallResultType))
				)
		self.callResult.set_result(result)


	async def waitForBL4PConnection(self) -> None:
		if not self.client.isBL4PConnected():
			logging.info('Order task: waiting for BL4P connection')
			await self.client.waitForBL4PConnection()
			logging.info('Order task: BL4P connection is present; continuing')


	async def doTrading(self) -> None:
		try:
			if isinstance(self.order, BuyOrder):
				await self.continueBuyTransaction()
				await self.publishOffer()
				tradeFunction = self.waitForIncomingTransaction
			elif isinstance(self.order, SellOrder):
				await self.continueSellTransaction()
				tradeFunction = self.doOfferSearch
			else:
				raise Exception('Unsupported order type - cannot use it in trade')

			while True:
				await tradeFunction()
				logging.info('Remaining in order: ' + \
					str(self.order.amount))

				if self.order.status == order.ORDER_STATUS_CANCEL_REQUESTED:
					logging.info('Order cancelation was requested - canceling it now')
					self.order.update(status=order.ORDER_STATUS_CANCELED)
					break
				elif self.order.amount <= 0:
					logging.info('Finished with order')
					self.order.update(status=order.ORDER_STATUS_COMPLETED)
					break

		except asyncio.CancelledError:
			logging.info('Order task got canceled')
			#We're cancelled, so just quit the function
		except:
			logging.exception('Exception in order task:')

		#These could have old values from something earlier that got
		#interrupted.
		#Set them back to None, so that the following un-publishing call can
		#proceed normally.
		self.callResult = None
		self.expectedCallResultType = None

		logging.info('End of order task, so removing the order from the market:')
		await self.unpublishOffer()

		self.client.backend.handleOrderTaskFinished(self.order.ID)


	async def doOfferSearch(self) -> None:
		'''
		Keeps searching for matching offers until it finds one.
		Then, it performs a single transaction based on the found offer.
		'''

		await self.waitForBL4PConnection()
		while True:
			try:
				queryResult = cast(messages.BL4PFindOffersResult,
					await self.call(messages.BL4PFindOffers(
						localOrderID=self.order.ID,

						query=self.order
						),
						messages.BL4PFindOffersResult)
					) #type: messages.BL4PFindOffersResult
			except messages.NoMessageHandler:
				logging.warning('BL4P is not connected, so we can\'t search for offers right now')
				await asyncio.sleep(1)
				continue

			if queryResult.offers: #found a matching offer
				await self.doTransactionBasedOnOffers(queryResult.offers)
				return

			if self.order.remoteOfferID is None:
				logging.info('Found no offers - making our own')
				await self.publishOffer()

			await asyncio.sleep(1)


	async def doTransactionBasedOnOffers(self, offers):
		logging.info('Received offers from BL4P')
		#TODO: filter on sensibility (e.g. max >= min for all conditions)

		#Check if offers actually match
		def matchesOurOrder(offer):
			ret = offer.matches(self.order)
			if not ret:
				logging.debug('Received an offer from BL4P that does not match our order - ignoring it')
			return ret
		offers = filter(matchesOurOrder, offers)

		#TODO (bug 8): filter counterOffers on acceptability
		#TODO (bug 8): sort counterOffers (e.g. on exchange rate)

		#Evaluate iterator to a list:
		offers = list(offers)

		#Start trade on the first in the list
		logging.info('Starting a transaction based on one of the offers')
		self.counterOffer = offers[0]
		await self.doTransaction()


	async def publishOffer(self) -> None:
		await self.waitForBL4PConnection()

		if self.order.remoteOfferID is not None:
			logging.info('The offer was already published - no need to re-publish it')
			return

		result = cast(messages.BL4PAddOfferResult,
			await self.call(messages.BL4PAddOffer(
				localOrderID=self.order.ID,

				offer=self.order
				),
				messages.BL4PAddOfferResult)
			) #type: messages.BL4PAddOfferResult

		remoteID = result.ID #type: int
		self.order.remoteOfferID = remoteID
		logging.info('Local ID %d gets remote ID %s' % (self.order.ID, remoteID))


	async def unpublishOffer(self) -> None:
		await self.waitForBL4PConnection()

		if self.order.remoteOfferID is None:
			logging.info('The offer was not published - no need to un-publish it')
			return

		await self.call(messages.BL4PRemoveOffer(
			localOrderID=self.order.ID,

			offerID=self.order.remoteOfferID,
			),
			messages.BL4PRemoveOfferResult)

		self.order.remoteOfferID = None


	########################################################################
	# Seller side
	########################################################################

	async def continueSellTransaction(self) -> None:
		assert isinstance(self.order, SellOrder)

		cursor = self.storage.execute(
			'SELECT ID from sellTransactions WHERE sellOrder = ? AND status != ? AND status != ?',
			[self.order.ID, TX_STATUS_FINISHED, TX_STATUS_CANCELED]
			) #type: Cursor
		IDs = [row[0] for row in cursor] #type: List[int]
		assert len(IDs) < 2 #TODO: properly report database inconsistency error
		if len(IDs) == 0:
			return #no transaction needs to be continued
		ID = IDs[0] #type: int

		logging.info('Found an unfinished transaction with ID %d - loading it' % ID)

		self.transaction = SellTransaction(self.storage, ID)
		storedCounterOffer = CounterOffer(self.storage, self.transaction.counterOffer) #type: CounterOffer
		self.counterOffer = storedCounterOffer.counterOffer

		#TODO: properly report database inconsistency error in case of KeyError
		method = \
		{
		TX_STATUS_INITIAL          : self.startTransactionOnBL4P,
		TX_STATUS_STARTED          : self.doSelfReportingOnBL4P,
		TX_STATUS_LOCKED           : self.doTransactionOnLightning,
		TX_STATUS_RECEIVED_PREIMAGE: self.receiveFiatFunds,
		}[self.transaction.status] #type: Callable[[], Awaitable[None]]
		await method()


	async def doTransaction(self) -> None:
		assert isinstance(self.order, SellOrder) #TODO (bug 13): enable buyer-initiated trade once supported
		assert self.counterOffer is not None

		logging.info('Doing trade for local order ID' + str(self.order.ID))
		logging.info('  local order: ' + str(self.order))
		logging.info('  counter offer: ' + str(self.counterOffer))

		cryptoAmountDivisor = settings.cryptoDivisor #type: int
		fiatAmountDivisor = settings.fiatDivisor #type: int

		#Choose the largest crypto amount accepted by both
		buyerCryptoAmount = min(
			cryptoAmountDivisor * self.order.bid.max_amount // self.order.bid.max_amount_divisor,
			cryptoAmountDivisor * self.counterOffer.ask.max_amount // self.counterOffer.ask.max_amount_divisor
			) #type: int
		logging.info('buyerCryptoAmount = ' + str(buyerCryptoAmount))
		assert buyerCryptoAmount > 0

		#The optimum fiat price for us is the highest:
		#this follows from the counter offer
		#eur = btc * (eur / btc)
		#    = btc * (bid / bid_divisor) / (ask / ask_divisor)
		#    = (btc * bid * ask_divisor) / (ask * bid_divisor)
		#Implementation note:
		#The correctness of this code might depend on Python's unlimited size integers.
		buyerFiatAmount = \
			(fiatAmountDivisor * buyerCryptoAmount   * self.counterOffer.bid.max_amount         * self.counterOffer.ask.max_amount_divisor) // \
			(                    cryptoAmountDivisor * self.counterOffer.bid.max_amount_divisor * self.counterOffer.ask.max_amount) #type: int
		maxBuyerFiatAmount = (buyerFiatAmount * self.counterOffer.bid.max_amount) // self.counterOffer.bid.max_amount_divisor #type: int
		if buyerFiatAmount > maxBuyerFiatAmount:
			buyerFiatAmount = maxBuyerFiatAmount
		logging.info('buyerFiatAmount = ' + str(buyerFiatAmount))
		assert buyerFiatAmount > 0

		#Choose the sender timeout limit as small as possible
		sender_timeout_delta_ms = getMinConditionValue(
			self.order, self.counterOffer,
			offer.Condition.SENDER_TIMEOUT
			) #type: int

		#Choose the locked timeout limit as large as possible
		locked_timeout_delta_s = getMaxConditionValue(
			self.order, self.counterOffer,
			offer.Condition.LOCKED_TIMEOUT
			) #type: int

		#Choose the CLTV expiry delta as small as possible
		CLTV_expiry_delta = getMinConditionValue(
			self.order, self.counterOffer,
			offer.Condition.CLTV_EXPIRY_DELTA
			) #type: int

		#TODO (bug 10): check if it's already in the database
		counterOfferID = CounterOffer.create(self.storage, self.counterOffer) #type: int

		sellTransactionID = SellTransaction.create(self.storage,
			sellOrder    = self.order.ID,
			counterOffer = counterOfferID,

			buyerFiatAmount   = buyerFiatAmount,
			buyerCryptoAmount  = buyerCryptoAmount,

			senderTimeoutDelta = sender_timeout_delta_ms,
			lockedTimeoutDelta = locked_timeout_delta_s,
			CLTVExpiryDelta    = CLTV_expiry_delta,
			) #type: int
		self.transaction = SellTransaction(self.storage, sellTransactionID)

		await self.startTransactionOnBL4P()


	async def startTransactionOnBL4P(self) -> None:
		assert isinstance(self.order, SellOrder)
		assert isinstance(self.transaction, SellTransaction)
		await self.waitForBL4PConnection()

		#Create transaction on the exchange:
		startResult = cast(messages.BL4PStartResult,
			await self.call(messages.BL4PStart(
				localOrderID = self.order.ID,

				amount = self.transaction.buyerFiatAmount,
				sender_timeout_delta_ms = self.transaction.senderTimeoutDelta,
				locked_timeout_delta_s = self.transaction.lockedTimeoutDelta,
				receiver_pays_fee = True
				),
				messages.BL4PStartResult)
			) #type: messages.BL4PStartResult

		assert startResult.senderAmount == self.transaction.buyerFiatAmount

		#Minimum: this is what we are prepared to receive
		fiatAmountDivisor = settings.fiatDivisor #type: int
		cryptoAmountDivisor = settings.cryptoDivisor #type: int
		buyerFiatAmount = self.transaction.buyerFiatAmount
		buyerCryptoAmount = self.transaction.buyerCryptoAmount
		minSellerFiatAmount = \
			(fiatAmountDivisor * buyerCryptoAmount   * self.order.ask.max_amount         * self.order.bid.max_amount_divisor) // \
			(                    cryptoAmountDivisor * self.order.ask.max_amount_divisor * self.order.bid.max_amount) #type: int
		logging.info('minSellerFiatAmount = ' + str(minSellerFiatAmount))
		assert minSellerFiatAmount <= buyerFiatAmount

		#Check that we're not receiving too little:
		sellerFiatAmount = startResult.receiverAmount
		logging.info('sellerFiatAmount = ' + str(sellerFiatAmount))
		if sellerFiatAmount < minSellerFiatAmount:
			logging.info('We\'ll receive too little; canceling the transaction.')
			await self.cancelIncomingFiatFunds()
			return

		self.transaction.update(
			sellerFiatAmount = sellerFiatAmount,
			paymentHash = startResult.paymentHash,
			status = TX_STATUS_STARTED,
			)

		await self.doSelfReportingOnBL4P()


	async def doSelfReportingOnBL4P(self) -> None:
		assert isinstance(self.order, SellOrder)
		assert isinstance(self.transaction, SellTransaction)
		assert self.counterOffer is not None
		await self.waitForBL4PConnection()

		await self.call(messages.BL4PSelfReport(
			localOrderID = self.order.ID,

			selfReport = \
				{
		                'paymentHash'         : self.transaction.paymentHash.hex(),
		                'offerID'             : str(self.counterOffer.ID),
		                'receiverCryptoAmount': formatCryptoAmount(self.transaction.buyerCryptoAmount),
		                'cryptoCurrency'      : self.order.bid.currency,
				},
			),
			messages.BL4PSelfReportResult)

		self.transaction.update(
			status = TX_STATUS_LOCKED,
			)

		await self.doTransactionOnLightning()


	async def doTransactionOnLightning(self) -> None:
		assert isinstance(self.order, SellOrder)
		assert isinstance(self.transaction, SellTransaction)
		assert self.counterOffer is not None

		maxSellerCryptoAmount = int(
			(1 + settings.maxLightningFee) *
			self.transaction.buyerCryptoAmount
			) #type: int
		logging.info('maxSellerCryptoAmount = ' + str(maxSellerCryptoAmount))

		#Send out over Lightning:
		lightningResult = cast(messages.LNPayResult,
			await self.call(messages.LNPay(
				localOrderID = self.order.ID,

				destinationNodeID     = self.counterOffer.address,
				paymentHash           = self.transaction.paymentHash,
				recipientCryptoAmount = self.transaction.buyerCryptoAmount,
				maxSenderCryptoAmount = maxSellerCryptoAmount,
				minCLTVExpiryDelta    = self.transaction.CLTVExpiryDelta,
				fiatAmount            = self.transaction.buyerFiatAmount,
				offerID               = self.counterOffer.ID,
				),
				messages.LNPayResult)
			) #type: messages.LNPayResult

		if lightningResult.paymentPreimage is None:
			#LN transaction failed, so revert everything we got so far
			logging.info('Outgoing Lightning transaction failed; canceling the transaction')
			await self.cancelIncomingFiatFunds()
			return

		assert sha256(lightningResult.paymentPreimage) == self.transaction.paymentHash
		logging.info('We got the preimage from the LN payment')

		self.transaction.update(
			sellerCryptoAmount = lightningResult.senderCryptoAmount,
			paymentPreimage = lightningResult.paymentPreimage,
			status = TX_STATUS_RECEIVED_PREIMAGE,
			)
		newAmount = self.order.amount - self.transaction.sellerCryptoAmount
		if newAmount < 0:
			#This is possible due to Lightning fees
			logging.info('We\'ve exceeded the order amount by ' + str(-newAmount))
			newAmount = 0
		self.order.setAmount(newAmount)

		await self.receiveFiatFunds()


	async def receiveFiatFunds(self) -> None:
		assert isinstance(self.order, SellOrder)
		assert isinstance(self.transaction, SellTransaction)
		await self.waitForBL4PConnection()

		receiveResult = cast(messages.BL4PReceiveResult,
			await self.call(messages.BL4PReceive(
				localOrderID=self.order.ID,

				paymentPreimage=self.transaction.paymentPreimage,
				),
				messages.BL4PReceiveResult)
			) #type: messages.BL4PReceiveResult

		self.transaction.update(
			status = TX_STATUS_FINISHED,
			)
		self.transaction = None

		logging.info('Sell transaction is finished')
		await self.updateOrderAfterTransaction()


	async def cancelIncomingFiatFunds(self) -> None:
		assert isinstance(self.order, SellOrder)
		assert isinstance(self.transaction, SellTransaction)
		await self.waitForBL4PConnection()

		await self.call(messages.BL4PCancelStart(
			localOrderID=self.order.ID,

			paymentHash=self.transaction.paymentHash,
			),
			messages.BL4PCancelStartResult)

		self.transaction.update(
			status = TX_STATUS_CANCELED,
			)
		self.transaction = None

		logging.info('Sell transaction is canceled')
		#TODO: do we need to call updateOrderAfterTransaction()?


	########################################################################
	# Buyer side
	########################################################################

	async def continueBuyTransaction(self) -> None:
		assert isinstance(self.order, BuyOrder)

		cursor = self.storage.execute(
			'SELECT ID from buyTransactions WHERE buyOrder = ? AND status != ? AND status != ?',
			[self.order.ID, TX_STATUS_FINISHED, TX_STATUS_CANCELED]
			) #type: Cursor
		IDs = [row[0] for row in cursor] #type: List[int]
		assert len(IDs) < 2 #TODO: properly report database inconsistency error
		if len(IDs) == 0:
			return #no transaction needs to be continued
		ID = IDs[0] #type: int

		logging.info('Found an unfinished transaction with ID %d - loading it' % ID)

		self.transaction = BuyTransaction(self.storage, ID)

		if self.transaction.status == TX_STATUS_INITIAL:
			logging.warning('For this unfinished transaction, we need to wait for lightningd to re-issue it to us')
			await self.waitForIncomingTransaction()
		else:
			#TODO: properly report database inconsistency error
			raise Exception('Invalid transaction status value in unfinished transaction')


	async def waitForIncomingTransaction(self) -> None:
		assert isinstance(self.order, BuyOrder)

		message = cast(messages.LNIncoming,
			await self.waitForIncomingMessage(messages.LNIncoming)
			) #type: messages.LNIncoming

		logging.info('Received incoming Lightning transaction')
		#TODO: log transaction characteristics
		#TODO: maybe refuse tx if we're not connected to BL4P

		#Check if this is a new notification for an already ongoing tx.
		cursor = self.storage.execute(
			'SELECT ID from buyTransactions WHERE paymentHash = ?',
			[message.paymentHash]
			) #type: Cursor
		transactions = [BuyTransaction(self.storage, row[0]) for row in cursor]
		if transactions:
			logging.info('A transaction with this payment hash already exists in our database')
			self.transaction = transactions[0]
			if self.transaction.paymentPreimage is not None:
				logging.info('We already have the preimage, so we claim the Lightning funds')
				await self.finishTransactionOnLightning()
				return

			#TODO (bug 19): maybe check if the incoming tx equals this tx?

			if self.transaction.status == TX_STATUS_CANCELED:
				logging.info('The transaction was canceled, so we cancel the Lightning tx')
				await self.cancelTransactionOnLightning()
			elif self.transaction.status == TX_STATUS_INITIAL:
				logging.info('The transaction was not finished yet, so try again to finish it')
				await self.sendFundsOnBL4P()
			else:
				#TODO: properly report database inconsistency error
				raise Exception('Invalid transaction status value in unfinished transaction')

			return

		#Check if lntx conforms to our order:
		counterOffer = Offer(
			#These are equivalent to our order, except for max_amount.
			#max_amount will be overwritten - see below
			bid=copy.deepcopy(self.order.ask),
			ask=copy.deepcopy(self.order.bid),

			#dummy values:
			address='',
			ID=0,

			#Don't specify sender_timeout: we can just try if we're still within the timeout
			#Don't specify locked_timeout: it is unknown to us; we will inform BL4P about our maximum
			) #type: offer.Offer
		counterOffer.bid.max_amount = message.cryptoAmount
		counterOffer.ask.max_amount = message.fiatAmount

		try:
			counterOffer.verifyMatches(self.order)
		except offer.MismatchError as error:
			logging.info('Received transaction did not match our order - refusing it.')
			logging.info('The mismatch is: ' + str(error))
			self.client.handleOutgoingMessage(messages.LNFail(
				paymentHash=message.paymentHash,
				))
			return

		#TODO: (bug 5) check max per-tx amount
		#TODO: (bug 5) check that we still have sufficient time
		#according to our cltv_expiry_delta

		#Check if remaining order size is sufficient:
		assert message.fiatAmount <= self.order.amount

		buyTransactionID = BuyTransaction.create(self.storage,
			buyOrder = self.order.ID,

			fiatAmount   = message.fiatAmount,
			cryptoAmount = message.cryptoAmount,

			paymentHash = message.paymentHash,
			) #type: int
		self.order.setAmount(self.order.amount - message.fiatAmount)
		self.transaction = BuyTransaction(self.storage, buyTransactionID)

		await self.sendFundsOnBL4P()


	async def sendFundsOnBL4P(self) -> None:
		assert isinstance(self.order, BuyOrder)
		assert isinstance(self.transaction, BuyTransaction)
		await self.waitForBL4PConnection()

		try:
			#Lock fiat funds:
			sendResult = cast(messages.BL4PSendResult,
				await self.call(messages.BL4PSend(
					localOrderID = self.order.ID,

					amount                     = self.transaction.fiatAmount,
					paymentHash                = self.transaction.paymentHash,
					max_locked_timeout_delta_s = self.order.getConditionMax(offer.Condition.LOCKED_TIMEOUT),
					selfReport                 = \
						{
						'paymentHash'         : self.transaction.paymentHash.hex(),
						'offerID'             : str(self.order.ID),
						'receiverCryptoAmount': formatCryptoAmount(self.transaction.cryptoAmount),
						'cryptoCurrency'      : self.order.ask.currency,
						},
					),
					messages.BL4PSendResult)
				) #type: messages.BL4PSendResult
		except BL4PError:
			logging.error('Error received from BL4P - transaction canceled')
			self.order.setAmount(self.order.amount + self.transaction.fiatAmount)
			self.transaction.update(
				status = TX_STATUS_CANCELED,
				)
			await self.cancelTransactionOnLightning()
			return

		#TODO: what if this asserion fails?
		assert sha256(sendResult.paymentPreimage) == self.transaction.paymentHash
		logging.info('We got the preimage from BL4P')

		self.transaction.update(
			paymentPreimage = sendResult.paymentPreimage,
			status = TX_STATUS_FINISHED,
			)

		await self.finishTransactionOnLightning()


	async def finishTransactionOnLightning(self) -> None:
		assert isinstance(self.order, BuyOrder)
		assert isinstance(self.transaction, BuyTransaction)

		#Receive crypto funds
		self.client.handleOutgoingMessage(messages.LNFinish(
			paymentHash=self.transaction.paymentHash,
			paymentPreimage=self.transaction.paymentPreimage,
			))
		self.transaction = None

		logging.info('Buy transaction is finished')
		await self.updateOrderAfterTransaction()


	async def cancelTransactionOnLightning(self) -> None:
		assert isinstance(self.order, BuyOrder)
		assert isinstance(self.transaction, BuyTransaction)

		self.client.handleOutgoingMessage(messages.LNFail(
			paymentHash=self.transaction.paymentHash,
			))
		self.transaction = None

		logging.info('Buy transaction is canceled')

		#TODO: is this really needed?
		await self.updateOrderAfterTransaction()


	########################################################################
	# Generic
	########################################################################

	async def updateOrderAfterTransaction(self) -> None:
		if self.order.remoteOfferID is None:
			return

		#Remove offer from the market
		logging.info('Removing old offer from the market')
		await self.unpublishOffer()

		#Re-add offer to the market
		if self.order.amount > 0:
			logging.info('Re-adding the offer to the market')
			await self.publishOffer()


	async def call(self, message: messages.AnyMessage, expectedResultType: Type) -> messages.AnyMessage:
		self.client.handleOutgoingMessage(message)
		return await self.waitForIncomingMessage(expectedResultType)


	async def waitForIncomingMessage(self, expectedResultType: Type) -> messages.AnyMessage:
		assert self.callResult is None
		self.callResult = asyncio.Future()
		self.expectedCallResultType = expectedResultType
		await self.callResult
		ret = self.callResult.result() #type: messages.AnyMessage

		#Special case for BL4P exceptions
		if isinstance(ret, messages.BL4PError):
			self.callResult = None
			self.expectedCallResultType = None
			raise BL4PError()

		assert isinstance(ret, expectedResultType)
		self.callResult = None
		self.expectedCallResultType = None
		return ret

