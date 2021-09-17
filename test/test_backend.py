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

import functools
import sys
import unittest
from unittest.mock import patch, Mock

from utils import asynciotest, MockCursor, MockStorage

sys.path.append('..')

import backend
import configuration
import messages
import order
import ordertask



class MockOrderTask:
	def __init__(self, client, storage, order):
		self.client = client
		self.storage = storage
		self.order = order
		self.started = False


	def startup(self):
		self.started = True



class TestBackend(unittest.TestCase):
	def setUp(self):
		self.outgoingMessages = []
		def handleOutgoingMessage(msg):
			self.outgoingMessages.append(msg)
		self.client = Mock()
		self.client.handleOutgoingMessage = handleOutgoingMessage

		self.backend = backend.Backend(self.client)


	def test_startup(self):
		self.assertEqual(self.backend.client, self.client)
		self.assertEqual(self.backend.handlerMethods,
			{
			messages.BuyCommand      : self.backend.handleBuyCommand,
			messages.SellCommand     : self.backend.handleSellCommand,
			messages.ListCommand     : self.backend.handleListCommand,
			messages.SetConfigCommand: self.backend.handleSetConfigCommand,

			messages.BL4PStartResult      : self.backend.handleBL4PResult,
			messages.BL4PSelfReportResult : self.backend.handleBL4PResult,
			messages.BL4PCancelStartResult: self.backend.handleBL4PResult,
			messages.BL4PSendResult       : self.backend.handleBL4PResult,
			messages.BL4PReceiveResult    : self.backend.handleBL4PResult,
			messages.BL4PAddOfferResult   : self.backend.handleBL4PResult,
			messages.BL4PRemoveOfferResult: self.backend.handleBL4PResult,
			messages.BL4PFindOffersResult : self.backend.handleBL4PResult,
			messages.BL4PError            : self.backend.handleBL4PResult,

			messages.LNIncoming: self.backend.handleLNIncoming,
			messages.LNPayResult: self.backend.handleLNPayResult,
			})

		self.backend.setLNAddress('LNAddress')
		self.assertEqual(self.backend.LNAddress, 'LNAddress')

		self.backend.setBL4PAddress('BL4PAddress')
		self.assertEqual(self.backend.BL4PAddress, 'BL4PAddress')

		def initStorage(s):
			s.sellOrders = \
			{
			41:
				{
				'ID': 41,
				'amount': 123,
				'limitRate': 20000,
				},
			42:
				{
				'ID': 42,
				'amount': 456,
				'limitRate': 21000,
				},
			}
			s.buyOrders = \
			{
			51:
				{
				'ID': 51,
				'amount': 789,
				'limitRate': 10000,
				},
			}

		MS = functools.partial(MockStorage, test=self, init=initStorage)
		with patch.object(backend.storage, 'Storage', MS):
			with patch.object(backend.ordertask, 'OrderTask', MockOrderTask):
				self.backend.startup('foo.file')

		self.assertTrue(isinstance(self.backend.storage, MockStorage))
		self.assertEqual(self.backend.storage.DBFile, 'foo.file')
		self.assertTrue(isinstance(self.backend.configuration, configuration.Configuration))
		self.assertEqual(self.backend.configuration.storage, self.backend.storage)

		self.assertEqual(set(self.backend.orderTasks.keys()), set([41, 42, 51]))
		for ot in self.backend.orderTasks.values():
			self.assertTrue(isinstance(ot, MockOrderTask))
			self.assertEqual(ot.client, self.client)
			self.assertEqual(ot.storage, self.backend.storage)
			self.assertTrue(ot.started)

		for ID in [41, 42]:
			self.assertTrue(isinstance(self.backend.orderTasks[ID].order, order.SellOrder))
			self.assertEqual(self.backend.storage.sellOrders[ID]['amount'], self.backend.orderTasks[ID].order.amount)
			self.assertEqual(self.backend.storage.sellOrders[ID]['limitRate'], self.backend.orderTasks[ID].order.limitRate)
		for ID in [51]:
			self.assertTrue(isinstance(self.backend.orderTasks[ID].order, order.BuyOrder))
			self.assertEqual(self.backend.storage.buyOrders[ID]['amount'], self.backend.orderTasks[ID].order.amount)
			self.assertEqual(self.backend.storage.buyOrders[ID]['limitRate'], self.backend.orderTasks[ID].order.limitRate)


	@asynciotest
	async def test_shutdown(self):
		count = []
		async def taskShutdown():
			count.append(1)
		
		self.backend.orderTasks = {41: Mock(), 42: Mock()}
		self.backend.orderTasks[41].shutdown = taskShutdown
		self.backend.orderTasks[42].shutdown = taskShutdown

		self.backend.storage = Mock()

		await self.backend.shutdown()

		self.assertEqual(len(count), 2)
		self.backend.storage.shutdown.assert_called_with()


	def test_handleBuyCommand(self):
		self.backend.storage = MockStorage(test = self)
		self.backend.LNAddress = 'LNAddress'
		self.backend.bl4pIsConnected = True

		cmd = Mock()
		cmd.commandID = 42
		cmd.amount = 123
		cmd.limitRate = 20000
		with patch.object(backend.ordertask, 'OrderTask', MockOrderTask):
			self.backend.handleBuyCommand(cmd)

		self.assertEqual(set(self.backend.orderTasks.keys()), set([61]))
		self.assertEqual(set(self.backend.storage.buyOrders.keys()), set([61]))

		ot = self.backend.orderTasks[61]
		stored = self.backend.storage.buyOrders[61]
		self.assertTrue(isinstance(ot, MockOrderTask))
		self.assertEqual(ot.client, self.client)
		self.assertEqual(ot.storage, self.backend.storage)
		self.assertTrue(ot.started)

		self.assertTrue(isinstance(ot.order, order.BuyOrder))
		self.assertEqual(stored['amount'], ot.order.amount)
		self.assertEqual(stored['limitRate'], ot.order.limitRate)
		self.assertEqual(stored['amount'], 123)
		self.assertEqual(stored['limitRate'], 20000)

		self.assertEqual(self.outgoingMessages,
			[messages.PluginCommandResult(
				commandID=42,
				result=None
			)])

	def test_handleBuyCommand_noBL4P(self):
		self.backend.storage = MockStorage(test = self)
		self.backend.LNAddress = 'LNAddress'
		self.backend.bl4pIsConnected = False

		cmd = Mock()
		cmd.commandID = 42
		cmd.amount = 123
		cmd.limitRate = 20000
		with patch.object(backend.ordertask, 'OrderTask', MockOrderTask):
			self.backend.handleBuyCommand(cmd)

		self.assertEqual(set(self.backend.orderTasks.keys()), set([]))
		self.assertEqual(set(self.backend.storage.buyOrders.keys()), set([]))

		self.assertEqual(self.outgoingMessages,
			[messages.PluginCommandError(
				commandID=42,
				code=1,
				message='Cannot perform this action while not connected to a BL4P server'
			)])


	def test_handleSellCommand(self):
		self.backend.storage = MockStorage(test = self)
		self.backend.BL4PAddress = 'BL4PAddress'
		self.backend.bl4pIsConnected = True

		cmd = Mock()
		cmd.commandID = 42
		cmd.amount = 123
		cmd.limitRate = 20000
		with patch.object(backend.ordertask, 'OrderTask', MockOrderTask):
			self.backend.handleSellCommand(cmd)

		self.assertEqual(set(self.backend.orderTasks.keys()), set([61]))
		self.assertEqual(set(self.backend.storage.sellOrders.keys()), set([61]))

		ot = self.backend.orderTasks[61]
		stored = self.backend.storage.sellOrders[61]
		self.assertTrue(isinstance(ot, MockOrderTask))
		self.assertEqual(ot.client, self.client)
		self.assertEqual(ot.storage, self.backend.storage)
		self.assertTrue(ot.started)

		self.assertTrue(isinstance(ot.order, order.SellOrder))
		self.assertEqual(stored['amount'], ot.order.amount)
		self.assertEqual(stored['limitRate'], ot.order.limitRate)
		self.assertEqual(stored['amount'], 123)
		self.assertEqual(stored['limitRate'], 20000)

		self.assertEqual(self.outgoingMessages,
			[messages.PluginCommandResult(
				commandID=42,
				result=None
			)])


	def test_handleSellCommand_noBL4P(self):
		self.backend.storage = MockStorage(test = self)
		self.backend.BL4PAddress = 'BL4PAddress'
		self.backend.bl4pIsConnected = False

		cmd = Mock()
		cmd.commandID = 42
		cmd.amount = 123
		cmd.limitRate = 20000
		with patch.object(backend.ordertask, 'OrderTask', MockOrderTask):
			self.backend.handleSellCommand(cmd)

		self.assertEqual(set(self.backend.orderTasks.keys()), set([]))
		self.assertEqual(set(self.backend.storage.sellOrders.keys()), set([]))

		self.assertEqual(self.outgoingMessages,
			[messages.PluginCommandError(
				commandID=42,
				code=1,
				message='Cannot perform this action while not connected to a BL4P server'
			)])


	def test_handleListCommand(self):
		class BuyOrder:
			pass

		class SellOrder:
			pass

		class Task:
			def __init__(self, cls, amount, limitRate):
				self.order = cls()
				self.order.amount = amount
				self.order.limitRate = limitRate

		self.backend.orderTasks = \
		{
		41: Task(BuyOrder, 123, 19000),
		51: Task(SellOrder, 456, 20000),
		52: Task(SellOrder, 789, 21000),
		}

		cmd = Mock()
		cmd.commandID = 42
		with patch.object(backend, 'BuyOrder', BuyOrder):
			with patch.object(backend, 'SellOrder', SellOrder):
				self.backend.handleListCommand(cmd)

		self.assertEqual(self.outgoingMessages,
			[messages.PluginCommandResult(
				commandID=42,
				result=\
					{
					'buy' :
						[
						{'amount': 123, 'limitRate': 19000},
						],
					'sell':
						[
						{'amount': 456, 'limitRate': 20000},
						{'amount': 789, 'limitRate': 21000},
						],
					}
			)])

		self.backend.orderTasks = \
		{
		41: Task(Mock, 123, 19000),
		}

		with patch.object(backend, 'BuyOrder', BuyOrder):
			with patch.object(backend, 'SellOrder', SellOrder):
				with self.assertRaises(Exception):
					self.backend.handleListCommand(cmd)


	def test_handleSetConfigCommand(self):
		self.backend.storage = MockStorage(test = self)
		self.backend.BL4PAddress = 'BL4PAddress'

		MS = MockStorage(test=self)
		self.backend.configuration = configuration.Configuration(MS)

		cmd = Mock()
		cmd.commandID = 42
		cmd.values = {'bl4p.apiKey': 'foo', 'bl4p.apiPrivateKey': 'bar'}

		self.backend.handleSetConfigCommand(cmd)

		self.assertEqual(self.backend.configuration.getValue('bl4p.apiKey'), 'foo')
		self.assertEqual(self.backend.configuration.getValue('bl4p.apiPrivateKey'), 'bar')
		self.assertEqual(MS.configuration['bl4p.apiKey'], 'foo')
		self.assertEqual(MS.configuration['bl4p.apiPrivateKey'], 'bar')

		self.assertEqual(self.outgoingMessages,
			[messages.PluginCommandResult(
				commandID=42,
				result=None
			)])


	def test_handleBL4PResult(self):
		self.backend.orderTasks = {41: Mock()}
		self.backend.orderTasks[41].setCallResult = Mock()

		result = Mock()
		result.request.localOrderID = 41
		self.backend.handleBL4PResult(result)

		self.backend.orderTasks[41].setCallResult.assert_called_with(result)


	def test_handleLNIncoming(self):
		msg = Mock()
		msg.offerID = 42
		msg.paymentHash = b'foobar'

		self.backend.orderTasks = {42: Mock()}
		self.backend.handleLNIncoming(msg)
		self.backend.orderTasks[42].setCallResult.assert_called_with(msg)

		self.backend.orderTasks = {41: Mock()}
		with patch.object(backend, 'logException', Mock()) as logException:
			self.backend.handleLNIncoming(msg)
			logException.assert_called_with()

		self.backend.orderTasks = {42: Mock()}
		self.backend.orderTasks[42].setCallResult = Mock(side_effect=Exception())
		with patch.object(backend, 'logException', Mock()) as logException:
			self.backend.handleLNIncoming(msg)
			logException.assert_called_with()


	def test_handleLNPayResult(self):
		msg = Mock()
		msg.localOrderID = 42
		self.backend.orderTasks = {42: Mock()}
		self.backend.handleLNPayResult(msg)
		self.backend.orderTasks[42].setCallResult.assert_called_with(msg)


	def test_handleOrderTaskFinished(self):
		self.backend.orderTasks = {41: 'foo', 42: 'bar'}
		self.backend.handleOrderTaskFinished(42)
		self.assertEqual(self.backend.orderTasks, {41: 'foo'})



if __name__ == '__main__':
	unittest.main(verbosity=2)

