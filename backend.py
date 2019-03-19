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

from bl4p_api import offer

from log import log, logException
import messages
import order
from order import BuyOrder, SellOrder
import ordertask
import settings



class Backend(messages.Handler):
	def __init__(self, client):
		messages.Handler.__init__(self, {
			messages.BuyCommand : self.handleBuyCommand,
			messages.SellCommand: self.handleSellCommand,

			messages.BL4PStartResult      : self.handleBL4PResult,
			messages.BL4PSendResult       : self.handleBL4PResult,
			messages.BL4PReceiveResult    : self.handleBL4PResult,
			messages.BL4PAddOfferResult   : self.handleBL4PResult,
			messages.BL4PRemoveOfferResult: self.handleBL4PResult,
			messages.BL4PFindOffersResult : self.handleBL4PResult,

			messages.LNIncoming        : self.handleLNIncoming,
			messages.LNOutgoingFinished: self.handleLNOutgoingFinished,
			messages.LNOutgoingFailed  : self.handleLNOutgoingFailed,
			})

		self.client = client
		self.orderTasks = {} #localID -> ordertask.OrderTask
		self.nextLocalOrderID = 0


	def setLNAddress(self, address):
		self.LNAddress = address


	def setBL4PAddress(self, address):
		self.BL4PAddress = address


	def updateOrder(self, order):
		pass #This is where an order can be stored to disk


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
		self.updateOrder(order)
		self.orderTasks[ID] = ordertask.OrderTask(self.client, order)
		self.orderTasks[ID].startup()


	def handleBL4PResult(self, result):
		localID = result.request.localOrderID
		self.orderTasks[localID].setCallResult(result)


	def handleLNIncoming(self, message):
		localID = message.offerID
		try:
			self.orderTasks[localID].setCallResult(message)
		except:
			log('Exception on trying to handle an incoming Lightning transaction for local ID ' + str(localID))
			logException()
			log('Apparently we can\'t handle the transaction right now, so we are refusing the incoming transaction.')
			self.client.handleOutgoingMessage(messages.LNFail(
				paymentHash=message.paymentHash
				))


	def handleLNOutgoingFinished(self, message):
		localID = message.localOrderID
		self.orderTasks[localID].setCallResult(message)


	def handleLNOutgoingFailed(self, message):
		localID = message.localOrderID
		self.orderTasks[localID].setCallResult(message)

