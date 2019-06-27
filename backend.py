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

from bl4p_api import offer

from log import log, logException
import messages
import order
from order import BuyOrder, SellOrder
import ordertask
import settings
import storage



class Backend(messages.Handler):
	def __init__(self, client):
		messages.Handler.__init__(self, {
			messages.BuyCommand : self.handleBuyCommand,
			messages.SellCommand: self.handleSellCommand,
			messages.ListCommand: self.handleListCommand,

			messages.BL4PStartResult      : self.handleBL4PResult,
			messages.BL4PCancelStartResult: self.handleBL4PResult,
			messages.BL4PSendResult       : self.handleBL4PResult,
			messages.BL4PReceiveResult    : self.handleBL4PResult,
			messages.BL4PAddOfferResult   : self.handleBL4PResult,
			messages.BL4PRemoveOfferResult: self.handleBL4PResult,
			messages.BL4PFindOffersResult : self.handleBL4PResult,
			messages.BL4PError            : self.handleBL4PResult,

			messages.LNIncoming : self.handleLNIncoming,
			messages.LNPayResult: self.handleLNPayResult,
			})

		self.storage = None

		self.client = client
		self.orderTasks = {} #localID -> ordertask.OrderTask


	def startup(self, DBFile):
		self.storage = storage.Storage(DBFile)

		#Loading existing orders and initializing order tasks:
		#TODO: This is wrong:
		#There may be orders where amount = 0, but there are still ongoing transactions.
		#These must be activated too.
		def loadOrders(tableName, orderClass, address):
			query = 'SELECT `ID` FROM `%s` WHERE `amount` > 0' % tableName
			cursor = self.storage.execute(query)
			for row in cursor:
				ID = row[0]
				order = orderClass(self.storage, ID, address)
				self.addOrder(order)

		loadOrders('sellOrders', SellOrder, self.BL4PAddress)
		loadOrders('buyOrders' , BuyOrder , self.LNAddress  )


	async def shutdown(self):
		for task in self.orderTasks.values():
			await task.shutdown()
		self.storage.shutdown()


	def setLNAddress(self, address):
		self.LNAddress = address


	def setBL4PAddress(self, address):
		self.BL4PAddress = address


	def handleBuyCommand(self, cmd):
		ID = BuyOrder.create(
			self.storage,
			limitRate = cmd.limitRate,
			amount = cmd.amount,
			)
		order = BuyOrder(self.storage, ID, self.LNAddress)
		self.addOrder(order)


	def handleSellCommand(self, cmd):
		ID = SellOrder.create(
			self.storage,
			limitRate = cmd.limitRate,
			amount = cmd.amount,
			)
		order = SellOrder(self.storage, ID, self.BL4PAddress)
		self.addOrder(order)


	def addOrder(self, order):
		self.orderTasks[order.ID] = ordertask.OrderTask(self.client, self.storage, order)
		self.orderTasks[order.ID].startup()


	def handleListCommand(self, cmd):
		sell = []
		buy = []
		for ID, task in self.orderTasks.items():
			order = {'limitRate': task.order.limitRate, 'amount': task.order.amount}
			if isinstance(task.order, SellOrder):
				sell.append(order)
			elif isinstance(task.order, BuyOrder):
				buy.append(order)
			else:
				raise Exception('Found an order of unknown type')
			

		self.client.handleOutgoingMessage(messages.PluginCommandResult(
			commandID = cmd.commandID,
			result = {'sell': sell, 'buy': buy}
			))


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


	def handleLNPayResult(self, message):
		localID = message.localOrderID
		self.orderTasks[localID].setCallResult(message)


	def handleOrderTaskFinished(self, ID):
		del self.orderTasks[ID]

