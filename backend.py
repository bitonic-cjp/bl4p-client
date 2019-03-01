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

import decimal
import hashlib

from bl4p_api import offer

from log import log
import messages
import order
from order import BuyOrder, SellOrder
import ordertask
import settings
from simplestruct import Struct



sha256 = lambda preimage: hashlib.sha256(preimage).digest()


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
STATUS_FINISHED = 2



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



class Backend(messages.Handler):
	def __init__(self, client):
		messages.Handler.__init__(self, {
			messages.BuyCommand : self.handleBuyCommand,
			messages.SellCommand: self.handleSellCommand,

			messages.BL4PStartResult: self.handleBL4PStartResult,
			messages.BL4PSendResult: self.handleBL4PSendResult,
			messages.BL4PReceiveResult: self.handleBL4PReceiveResult,

			messages.BL4PAddOfferResult: self.handleBL4PAddOfferResult,
			messages.BL4PFindOffersResult : self.handleBL4PFindOffersResult,

			messages.LNIncoming: self.handleLNIncoming,
			messages.LNOutgoingFinished: self.handleLNOutgoingFinished,
			})

		self.client = client
		self.orders = {}
		self.orderTasks = {}
		self.transactions = {}
		self.nextLocalOrderID = 0
		self.nextLocalTransactionID = 0


	def setLNAddress(self, address):
		self.LNAddress = address


	def setBL4PAddress(self, address):
		self.BL4PAddress = address



	def getOrders(self):
		return self.orders.values()


	def getOrder(self, localID):
		return self.orders[localID]


	def handleBuyCommand(self, cmd):
		order = BuyOrder(
			self.LNAddress,
			limitRate = decimal.Decimal(cmd.limitRate) / settings.cryptoDivisor,
			totalBidAmount = decimal.Decimal(cmd.amount),
			)
		self.addOrder(order)


	def handleSellCommand(self, cmd):
		order = SellOrder(
			self.BL4PAddress,
			limitRate = decimal.Decimal(cmd.limitRate) / settings.cryptoDivisor,
			totalBidAmount = decimal.Decimal(cmd.amount),
			)
		self.addOrder(order)


	def addOrder(self, order):
		ID = self.nextLocalOrderID
		self.nextLocalOrderID += 1
		order.ID = ID
		self.orders[ID] = order
		self.orderTasks[ID] = ordertask.OrderTask(self.client, ID)
		self.orderTasks[ID].startup()


	def handleBL4PAddOfferResult(self, result):
		localID = result.request.offer.ID
		self.orderTasks[localID].setCallResult(result)


	def handleBL4PFindOffersResult(self, result):
		localID = result.request.query.ID
		self.orderTasks[localID].setCallResult(result)


	def startTransaction(self, localID, counterOffer):
		ownOrder = self.orders[localID]
		if isinstance(ownOrder, BuyOrder):
			self.startBuyTransaction(localID, counterOffer)
		elif isinstance(ownOrder, SellOrder):
			self.startSellTransaction(localID, counterOffer)
		else:
			raise Exception('Unsupported order type - cannot use it in trade')


	def startBuyTransaction(self, localID, counterOffer):
		pass #TODO: enable buyer-initiated trade once supported


	def startSellTransaction(self, localID, counterOffer):
		ownOrder = self.orders[localID]

		log('Doing trade for local order ID' + str(localID))
		log('  local order: ' + str(ownOrder))
		log('  counter offer: ' + str(counterOffer))

		#Choose the largest fiat amount accepted by both
		fiatAmountDivisor = settings.fiatDivisor
		fiatAmount = min(
			fiatAmountDivisor * ownOrder.ask.max_amount // ownOrder.ask.max_amount_divisor,
			fiatAmountDivisor * counterOffer.bid.max_amount // counterOffer.bid.max_amount_divisor
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
			(cryptoAmountDivisor * fiatAmount        * counterOffer.ask.max_amount         * counterOffer.bid.max_amount_divisor) // \
			(                      fiatAmountDivisor * counterOffer.ask.max_amount_divisor * counterOffer.bid.max_amount)
		#Maximum: this is what we are prepared to pay
		maxCryptoAmount = \
			(cryptoAmountDivisor * fiatAmount        * ownOrder.bid.max_amount         * ownOrder.ask.max_amount_divisor) // \
			(                      fiatAmountDivisor * ownOrder.bid.max_amount_divisor * ownOrder.ask.max_amount)
		assert minCryptoAmount >= 0
		assert maxCryptoAmount >= minCryptoAmount

		#Choose the sender timeout limit as small as possible
		sender_timeout_delta_ms = getMinConditionValue(
			ownOrder, counterOffer,
			offer.Condition.SENDER_TIMEOUT
			)

		#Choose the locked timeout limit as large as possible
		locked_timeout_delta_s = getMaxConditionValue(
			ownOrder, counterOffer,
			offer.Condition.LOCKED_TIMEOUT
			)

		#Choose the CLTV expiry delta as small as possible
		CLTV_expiry_delta = getMinConditionValue(
			ownOrder, counterOffer,
			offer.Condition.CLTV_EXPIRY_DELTA
			)

		tx = SellTransaction(
			status = STATUS_INITIAL,
			localOrderID = localID,
			counterOffer = counterOffer,
			fiatAmount = fiatAmount,
			minCryptoAmount = minCryptoAmount,
			maxCryptoAmount = maxCryptoAmount,
			sender_timeout_delta_ms = sender_timeout_delta_ms,
			locked_timeout_delta_s = locked_timeout_delta_s,
			CLTV_expiry_delta = CLTV_expiry_delta,
			)

		txID = self.addTransaction(tx)
		self.orders[localID].status = order.STATUS_TRADING

		#Create transaction on the exchange:
		self.client.handleOutgoingMessage(messages.BL4PStart(
			localTransactionID = txID,

			amount = tx.fiatAmount,
			sender_timeout_delta_ms = tx.sender_timeout_delta_ms,
			locked_timeout_delta_s = tx.locked_timeout_delta_s,
			receiver_pays_fee = True
			))


	def addTransaction(self, tx):
		ID = self.nextLocalTransactionID
		self.nextLocalTransactionID += 1
		self.transactions[ID] = tx
		return ID


	def handleBL4PStartResult(self, message):
		txID = message.request.localTransactionID
		tx = self.transactions[txID]

		assert message.senderAmount == tx.fiatAmount
		#TODO: check that we're not paying too much fees to BL4P

		tx.senderAmount = message.senderAmount     #Sender of *fiat*
		tx.receiverAmount = message.receiverAmount #Receiver of *fiat*
		tx.paymentHash = message.paymentHash
		tx.status = STATUS_LOCKED

		#Send out over Lightning:
		self.client.handleOutgoingMessage(messages.LNPay(
			destinationNodeID=tx.counterOffer.address,
			paymentHash=tx.paymentHash,
			recipientCryptoAmount=tx.minCryptoAmount,
			maxSenderCryptoAmount=tx.maxCryptoAmount,
			minCLTVExpiryDelta=tx.CLTV_expiry_delta,
			fiatAmount=tx.fiatAmount,
			offerID=tx.counterOffer.ID,
			))


	def handleLNIncoming(self, message):
		#TODO: check if this is a new notification for an already
		#ongoing tx.
		#In that case, simply send back the payment preimage again.

		localID = message.offerID
		ownOrder = self.getOrder(localID)

		#TODO: proper handling of failing this condition:
		assert self.orders[localID].status == order.STATUS_IDLE

		#TODO: check if lntx conforms to our order
		#TODO: check if remaining order size is sufficient

		tx = BuyTransaction(
			status = STATUS_LOCKED,
			localOrderID = localID,
			cryptoAmount = message.cryptoAmount,
			fiatAmount = message.fiatAmount,
			paymentHash = message.paymentHash,
			)

		log('Received incoming Lightning transaction')

		txID = self.addTransaction(tx)
		self.orders[localID].status = order.STATUS_TRADING

		#Lock fiat funds:
		self.client.handleOutgoingMessage(messages.BL4PSend(
			localTransactionID = txID,

			amount=tx.fiatAmount,
			paymentHash=tx.paymentHash,
			))


	def handleBL4PSendResult(self, message):
		txID = message.request.localTransactionID
		tx = self.transactions[txID]

		assert sha256(message.paymentPreimage) == tx.paymentHash
		log('We got the preimage from BL4P')

		tx.paymentPreimage = message.paymentPreimage
		tx.status = STATUS_FINISHED

		#Receive crypto funds
		self.client.handleOutgoingMessage(messages.LNFinish(
			paymentHash=tx.paymentHash,
			paymentPreimage=tx.paymentPreimage,
			))

		#TODO: clean up everything


	def handleLNOutgoingFinished(self, message):
		assert sha256(message.paymentPreimage) == message.paymentHash
		log('We got the preimage from the LN payment')

		for txID, tx in self.transactions.items():
			if tx.paymentHash != message.paymentHash or not isinstance(tx, SellTransaction):
				continue

			tx.paymentPreimage = message.paymentPreimage
			tx.status = STATUS_FINISHED

			#Receive fiat funds:
			self.client.handleOutgoingMessage(messages.BL4PReceive(
				localTransactionID=txID,
				paymentPreimage=tx.paymentPreimage,
				))


	def handleBL4PReceiveResult(self, message):
		txID = message.request.localTransactionID
		log('Transaction is finished')
		#TODO: clean up everything

