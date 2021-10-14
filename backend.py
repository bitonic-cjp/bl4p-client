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

import logging
from typing import Any, Dict, List, Optional, Type, Union, TYPE_CHECKING

from bl4p_api import offer

if TYPE_CHECKING:
	import bl4p_plugin #pragma: nocover

import configuration
import messages
import order
from order import BuyOrder, SellOrder
import ordertask
import settings
from simplestruct import Struct
import storage



def requireBL4PConnection(method):
	def wrapper(self, cmd):
		if not self.client.isBL4PConnected():
			self.client.handleOutgoingMessage(messages.PluginCommandError(
				commandID = cmd.commandID,
				code = 1,
				message = 'Cannot perform this action while not connected to a BL4P server'
				))
			return
		method(self, cmd)
	return wrapper



class Backend(messages.Handler):
	def __init__(self, client: 'bl4p_plugin.BL4PClient') -> None:
		messages.Handler.__init__(self, {
			messages.BuyCommand      : self.handleBuyCommand,
			messages.SellCommand     : self.handleSellCommand,
			messages.ListCommand     : self.handleListCommand,
			messages.CancelCommand   : self.handleCancelCommand,
			messages.SetConfigCommand: self.handleSetConfigCommand,
			messages.GetConfigCommand: self.handleGetConfigCommand,

			messages.BL4PStartResult      : self.handleBL4PResult,
			messages.BL4PSelfReportResult : self.handleBL4PResult,
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


		self.client = client #type: bl4p_plugin.BL4PClient
		self.orderTasks = {} #type: Dict[int, ordertask.OrderTask] #localID -> OrderTask


	def startup(self, DBFile: str) -> None:
		self.storage = storage.Storage(DBFile) #type: storage.Storage
		self.configuration = configuration.Configuration(self.storage) #type: configuration.Configuration

		#Loading existing orders and initializing order tasks:
		def loadOrders(tableName: str, orderClass: Type[Union[SellOrder, BuyOrder]], address: str) -> None:
			query = 'SELECT `ID` FROM `%s` WHERE `status` = %d OR `status` = %d' % \
				(tableName, order.ORDER_STATUS_ACTIVE, order.ORDER_STATUS_CANCEL_REQUESTED) #type: str
			cursor = self.storage.execute(query) #type: storage.Cursor
			for row in cursor:
				ID = row[0] #type: int
				orderObj = orderClass(self.storage, ID, address) #type: Union[SellOrder, BuyOrder]
				self.addOrder(orderObj)

		loadOrders('sellOrders', SellOrder, self.BL4PAddress)
		loadOrders('buyOrders' , BuyOrder , self.LNAddress  )


	async def shutdown(self) -> None:
		#self.orderTasks may be modified while we do this,
		#so we make a copy first:
		tasks = list(self.orderTasks.values()) #type: List[ordertask.OrderTask]
		for task in tasks:
			await task.shutdown()
		self.storage.shutdown()


	def setLNAddress(self, address: str) -> None:
		self.LNAddress = address #type: str


	def setBL4PAddress(self, address: str) -> None:
		self.BL4PAddress = address #type: str


	@requireBL4PConnection
	def handleBuyCommand(self, cmd: messages.BuyCommand) -> None:
		ID = BuyOrder.create(
			self.storage,
			limitRate = cmd.limitRate,
			amount = cmd.amount,
			) #type: int
		order = BuyOrder(self.storage, ID, self.LNAddress) #type: BuyOrder
		self.addOrder(order)

		self.client.handleOutgoingMessage(messages.PluginCommandResult(
			commandID = cmd.commandID,
			result = None
			))


	@requireBL4PConnection
	def handleSellCommand(self, cmd: messages.SellCommand) -> None:
		ID = SellOrder.create(
			self.storage,
			limitRate = cmd.limitRate,
			amount = cmd.amount,
			) #type: int
		order = SellOrder(self.storage, ID, self.BL4PAddress) #type: SellOrder
		self.addOrder(order)

		self.client.handleOutgoingMessage(messages.PluginCommandResult(
			commandID = cmd.commandID,
			result = None
			))


	def addOrder(self, order: Union[SellOrder, BuyOrder]) -> None:
		self.orderTasks[order.ID] = ordertask.OrderTask(self.client, self.storage, order)
		self.orderTasks[order.ID].startup()


	def handleListCommand(self, cmd: messages.ListCommand) -> None:
		sell = [] #type: List[Dict[str, Any]]
		buy  = [] #type: List[Dict[str, Any]]
		for task in self.orderTasks.values():
			order = task.getListInfo() #type: Dict[str, Any]
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


	def handleCancelCommand(self, cmd: messages.CancelCommand) -> None:
		try:
			task = self.orderTasks[cmd.orderID]
		except KeyError:
			self.client.handleOutgoingMessage(messages.PluginCommandError(
				commandID = cmd.commandID,
				code = 2,
				message = 'There is no active order with ID ' + str(cmd.orderID)
				))
			return

		task.cancel()

		self.client.handleOutgoingMessage(messages.PluginCommandResult(
			commandID = cmd.commandID,
			result = None
			))


	def handleSetConfigCommand(self, cmd: messages.SetConfigCommand) -> None:
		for k, v in cmd.values.items():
			self.configuration.setValue(k, v)

		self.client.handleOutgoingMessage(messages.PluginCommandResult(
			commandID = cmd.commandID,
			result = None
			))


	def handleGetConfigCommand(self, cmd: messages.GetConfigCommand) -> None:
		values = self.configuration.getAllValues() #type: Dict[str, str]

		self.client.handleOutgoingMessage(messages.PluginCommandResult(
			commandID = cmd.commandID,
			result = {'values': values}
			))


	def handleBL4PResult(self, result: messages.BL4PResult) -> None:
		localID = result.request.localOrderID #type: int
		self.orderTasks[localID].setCallResult(result)


	def handleLNIncoming(self, message: messages.LNIncoming) -> None:
		localID = message.offerID #type: int
		try:
			self.orderTasks[localID].setCallResult(message)
		except:
			logging.exception('Exception on trying to handle an incoming Lightning transaction for local ID ' + str(localID))
			logging.error('Apparently we can\'t handle the transaction right now, so we are refusing the incoming transaction.')
			self.client.handleOutgoingMessage(messages.LNFail(
				paymentHash=message.paymentHash
				))


	def handleLNPayResult(self, message: messages.LNPayResult) -> None:
		localID = message.localOrderID #type: int
		self.orderTasks[localID].setCallResult(message)


	def handleOrderTaskFinished(self, ID: int) -> None:
		logging.info('Order task %d is finished, de-registering it' % ID)
		del self.orderTasks[ID]

