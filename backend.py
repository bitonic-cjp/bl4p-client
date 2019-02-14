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

from log import log
import messages
import order
from order import BuyOrder, SellOrder
import transaction
from transaction import BuyTransaction, SellTransaction
import settings



class Backend:
	def __init__(self):
		self.orders = {}
		self.transactions = {}
		self.outgoingMessageQueue = []
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


	def getNextOutgoingMessage(self):
		return self.outgoingMessageQueue.pop(0)


	def addOutgoingMessage(self, message):
		self.outgoingMessageQueue.append(message)


	def handleIncomingMessage(self, message):
		{
		messages.BuyCommand : self.handleBuyCommand,
		messages.SellCommand: self.handleSellCommand,

		messages.BL4PStartResult: self.handleBL4PStartResult,

		messages.BL4PAddOfferResult: self.handleBL4PAddOfferResult,
		}[message.__class__](message)


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


	def handleBL4PAddOfferResult(self, result):
		#Note: the request was sent by Trader

		localID = result.request.offer.ID
		remoteID = result.ID
		order = self.orders[localID]
		order.remoteOfferID = remoteID
		log('Local ID %d gets remote ID %s' % (localID, remoteID))


	def startTransaction(self, localID, counterOffer):
		ownOrder = self.orders[localID]
		if isinstance(ownOrder, BuyOrder):
			return
			#TODO: enable buyer-initiated trade once supported
			#tx = BuyTransaction(localID)
			#TODO: fill with offer data
		elif isinstance(ownOrder, SellOrder):
			tx = SellTransaction(localID)
			#TODO: fill with offer data
		else:
			raise Exception('Unsupported order type - cannot use it in trade')

		log('Doing trade for local order ID' + str(localID))
		log('  local order: ' + str(ownOrder))
		log('  counter offer: ' + str(counterOffer))

		tx.initiateFromCounterOffer(ownOrder, counterOffer)

		txID = self.addTransaction(tx)
		self.orders[localID].status = order.STATUS_TRADING

		#Create transaction on the exchange:
		self.addOutgoingMessage(messages.BL4PStart(
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

		#Send out over Lightning:
		self.addOutgoingMessage(messages.LNPay(
			destinationNodeID=tx.counterOffer.address,
			paymentHash=tx.paymentHash,
			recipientCryptoAmount=tx.minCryptoAmount,
			maxSenderCryptoAmount=tx.maxCryptoAmount,
			minCLTVExpiryDelta=tx.CLTV_expiry_delta,
			fiatAmount=tx.fiatAmount,
			offerID=tx.counterOffer.ID,
			))

		tx.senderAmount = message.senderAmount     #Sender of *fiat*
		tx.receiverAmount = message.receiverAmount #Receiver of *fiat*
		tx.paymentHash = message.paymentHash
		tx.status = transaction.STATUS_LOCKED

