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
from order import BuyOrder, SellOrder
import settings



class Backend:
	def __init__(self):
		self.orders = {}
		self.outgoingMessageQueue = []
		self.nextLocalOrderID = 0


	def setLNAddress(self, address):
		self.LNAddress = address


	def setBL4PAddress(self, address):
		self.BL4PAddress = address



	def getOrders(self):
		return self.orders.values()


	def getNextOutgoingMessage(self):
		return self.outgoingMessageQueue.pop(0)


	def addOutgoingMessage(self, message):
		self.outgoingMessageQueue.append(message)


	def handleIncomingMessage(self, message):
		{
		messages.BuyCommand : self.handleBuyCommand,
		messages.SellCommand: self.handleSellCommand,

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
		localID = result.request.offer.ID
		remoteID = result.ID
		order = self.orders[localID]
		order.remoteOfferID = remoteID
		log('Local ID %d gets remote ID %s' % (localID, remoteID))

