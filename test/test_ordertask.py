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
import sys
import time
import unittest
from unittest.mock import patch, Mock

from utils import asynciotest

sys.path.append('..')

from bl4p_api import offer
import messages
from order import Order
import ordertask



sha256 = lambda preimage: hashlib.sha256(preimage).digest() 



class MockCursor(list):
	def __init__(self, data, **kwargs):
		list.__init__(self, data)
		for k,v in kwargs.items():
			setattr(self, k, v)

	def fetchone(self):
		return self.pop(0)



class MockStorage:
	def __init__(self, test, startCount):
		self.test = test
		self.reset(startCount)


	def reset(self, startCount):
		self.buyOrders = {}
		self.buyTransactions = {}
		self.sellOrders = {}
		self.sellTransactions = {}
		self.counterOffers = {}
		self.counter = startCount


	def execute(self, query, data):
		if query.startswith('INSERT INTO buyTransactions'):
			names = query[query.index('(')+1:query.index(')')]
			names = names.replace('`','').split(',')
			self.test.assertEqual(len(names), len(data))
			self.buyTransactions[self.counter] = \
			{
			names[i]:data[i]
			for i in range(len(names))
			}
			self.buyTransactions[self.counter]['ID'] = self.counter
			self.counter += 1
			return MockCursor([], lastrowid=self.counter-1)
		elif query.startswith('UPDATE buyTransactions SET'):
			ID = data[-1]
			data = data[:-1]
			names = query[query.index('(')+1:query.index(')')]
			names = names.replace('`','').split(',')
			self.test.assertEqual(len(names), len(data))
			for i in range(len(names)):
				self.buyTransactions[ID][names[i]] = data[i]
			return MockCursor([])
		elif query == 'SELECT * from buyTransactions WHERE `ID` = ?':
			data = self.buyTransactions[data[0]]
			keys = list(data.keys())
			values = [data[k] for k in keys]
			return MockCursor([values], description=[(k,) for k in keys])
		elif query == 'SELECT ID from buyTransactions WHERE buyOrder = ? AND status != ?':
			self.test.assertEqual(data[1:], [ordertask.STATUS_FINISHED])
			values = \
			[
			[tx['ID']]
			for tx in self.buyTransactions.values()
			if tx['buyOrder'] == data[0] and tx['status'] != ordertask.STATUS_FINISHED
			]
			return MockCursor(values)

		elif query.startswith('INSERT INTO buyOrders'):
			names = query[query.index('(')+1:query.index(')')]
			names = names.replace('`','').split(',')
			self.test.assertEqual(len(names), len(data))
			self.buyOrders[self.counter] = \
			{
			names[i]:data[i]
			for i in range(len(names))
			}
			self.buyOrders[self.counter]['ID'] = self.counter
			self.counter += 1
			return MockCursor([], lastrowid=self.counter-1)
		elif query == 'SELECT * from buyOrders WHERE `ID` = ?':
			data = self.buyOrders[data[0]]
			keys = list(data.keys())
			values = [data[k] for k in keys]
			return MockCursor([values], description=[(k,) for k in keys])

		elif query.startswith('INSERT INTO sellTransactions'):
			names = query[query.index('(')+1:query.index(')')]
			names = names.replace('`','').split(',')
			self.test.assertEqual(len(names), len(data))
			self.sellTransactions[self.counter] = \
			{
			names[i]:data[i]
			for i in range(len(names))
			}
			self.sellTransactions[self.counter]['ID'] = self.counter
			self.counter += 1
			return MockCursor([], lastrowid=self.counter-1)
		elif query.startswith('UPDATE sellTransactions SET'):
			ID = data[-1]
			data = data[:-1]
			names = query[query.index('(')+1:query.index(')')]
			names = names.replace('`','').split(',')
			self.test.assertEqual(len(names), len(data))
			for i in range(len(names)):
				self.sellTransactions[ID][names[i]] = data[i]
			return MockCursor([])
		elif query == 'SELECT * from sellTransactions WHERE `ID` = ?':
			data = self.sellTransactions[data[0]]
			keys = list(data.keys())
			values = [data[k] for k in keys]
			return MockCursor([values], description=[(k,) for k in keys])
		elif query == 'SELECT ID from sellTransactions WHERE sellOrder = ? AND status != ?':
			self.test.assertEqual(data[1:], [ordertask.STATUS_FINISHED])
			values = \
			[
			[tx['ID']]
			for tx in self.sellTransactions.values()
			if tx['sellOrder'] == data[0] and tx['status'] != ordertask.STATUS_FINISHED
			]
			return MockCursor(values)

		elif query.startswith('INSERT INTO sellOrders'):
			names = query[query.index('(')+1:query.index(')')]
			names = names.replace('`','').split(',')
			self.test.assertEqual(len(names), len(data))
			self.sellOrders[self.counter] = \
			{
			names[i]:data[i]
			for i in range(len(names))
			}
			self.sellOrders[self.counter]['ID'] = self.counter
			self.counter += 1
			return MockCursor([], lastrowid=self.counter-1)
		elif query.startswith('UPDATE sellOrders SET'):
			ID = data[-1]
			data = data[:-1]
			names = query[query.index('(')+1:query.index(')')]
			names = names.replace('`','').split(',')
			self.test.assertEqual(len(names), len(data))
			for i in range(len(names)):
				self.sellOrders[ID][names[i]] = data[i]
			return MockCursor([])
		elif query == 'SELECT * from sellOrders WHERE `ID` = ?':
			data = self.sellOrders[data[0]]
			keys = list(data.keys())
			values = [data[k] for k in keys]
			return MockCursor([values], description=[(k,) for k in keys])

		elif query == 'INSERT INTO counterOffers (`blob`) VALUES (?)':
			self.counterOffers[self.counter] = \
			{
			'ID': self.counter,
			'blob': data[0],
			}
			self.counter += 1
			return MockCursor([], lastrowid=self.counter-1)
		elif query == 'SELECT * from counterOffers WHERE `ID` = ?':
			data = self.counterOffers[data[0]]
			keys = list(data.keys())
			values = [data[k] for k in keys]
			return MockCursor([values], description=[(k,) for k in keys])

		raise Exception('Query not recognized: ' + str(query))



class TestOrderTask(unittest.TestCase):
	def test_BuyTransaction(self):
		with patch.object(ordertask.StoredObject, 'create', Mock(return_value=43)):
			self.assertEqual(ordertask.BuyTransaction.create('foo', 'baa', 'bab', 'bac', 'bad'), 43)

			ordertask.StoredObject.create.assert_called_once_with(
				'foo', 'buyTransactions',
				buyOrder='baa', fiatAmount='bab', cryptoAmount='bac', paymentHash='bad',
				status=0, paymentPreimage=None,
				)

			storage = Mock()
			cursor = Mock()
			cursor.description = [['ID'], ['status'], ['paymentHash']]
			cursor.fetchone = Mock(return_value = [42, 1, b'cafecafe'])
			storage.execute = Mock(return_value=cursor)

			buy = ordertask.BuyTransaction(storage, 42)

			self.assertEqual(buy.ID, 42)
			self.assertEqual(buy._tableName, 'buyTransactions')
			self.assertEqual(buy.status, 1)
			self.assertEqual(buy.paymentHash, b'cafecafe')


	def test_SellTransaction(self):
		with patch.object(ordertask.StoredObject, 'create', Mock(return_value=43)):
			self.assertEqual(ordertask.SellTransaction.create('foo', 'baa', 'bab', 'bac', 'bad', 'bae', 'baf', 'bag', 'bah'), 43)

			ordertask.StoredObject.create.assert_called_once_with(
				'foo', 'sellTransactions',
				sellOrder='baa', counterOffer='bab', senderFiatAmount='bac', maxSenderCryptoAmount='bad', receiverCryptoAmount='bae', senderTimeoutDelta='baf', lockedTimeoutDelta='bag', CLTVExpiryDelta='bah',
				status=0, receiverFiatAmount=None, senderCryptoAmount=None, paymentHash=None, paymentPreimage=None,
				)

			storage = Mock()
			cursor = Mock()
			cursor.description = [['ID'], ['status'], ['paymentHash']]
			cursor.fetchone = Mock(return_value = [42, 1, b'cafecafe'])
			storage.execute = Mock(return_value=cursor)

			sell = ordertask.SellTransaction(storage, 42)

			self.assertEqual(sell.ID, 42)
			self.assertEqual(sell._tableName, 'sellTransactions')
			self.assertEqual(sell.status, 1)
			self.assertEqual(sell.paymentHash, b'cafecafe')


	def test_CounterOffer(self):
		with patch.object(ordertask.StoredObject, 'create', Mock(return_value=43)):
			PB2 = Mock()
			PB2.SerializeToString = Mock(return_value=b'bar')
			counterOffer = Mock()
			counterOffer.toPB2 = Mock(return_value=PB2)

			self.assertEqual(ordertask.CounterOffer.create('foo', counterOffer), 43)

			ordertask.StoredObject.create.assert_called_once_with(
				'foo', 'counterOffers', blob=b'bar')

			storage = Mock()
			cursor = Mock()
			cursor.description = [['ID'], ['blob']]
			cursor.fetchone = Mock(return_value = [42, b'cafecafe'])
			storage.execute = Mock(return_value=cursor)

			ParseFromString = Mock()
			def fromPB2(co):
				self.assertTrue(isinstance(co, ordertask.offer_pb2.Offer))
				return 'bar'

			with patch.object(ordertask.offer_pb2.Offer, 'ParseFromString', ParseFromString):
				with patch.object(ordertask.Offer, 'fromPB2', fromPB2):
					co = ordertask.CounterOffer(storage, 42)

			ParseFromString.assert_called_once_with(b'cafecafe')

			self.assertEqual(co.ID, 42)
			self.assertEqual(co._tableName, 'counterOffers')
			self.assertEqual(co.blob, b'cafecafe')
			self.assertEqual(co.counterOffer, 'bar')


	def test_constructor(self):
		client = object()
		storage = object()
		order = object()
		task = ordertask.OrderTask(client, storage, order)

		self.assertEqual(task.client, client)
		self.assertEqual(task.storage, storage)
		self.assertEqual(task.order, order)
		self.assertEqual(task.counterOffer, None)
		self.assertEqual(task.transaction, None)


	@asynciotest
	async def test_task(self):
		task = ordertask.OrderTask(None, None, None)

		result = []

		async def count():
			try:
				i = 1
				while True:
					await asyncio.sleep(0.1)
					result.append(i)
					i += 1
			except asyncio.CancelledError:
				pass

		task.doTrading = count
		task.startup()
		await asyncio.sleep(0.35)
		await task.shutdown()
		self.assertEqual(result, [1, 2, 3])

		result = []

		async def countTo3():
			for i in range(1, 4):
				await asyncio.sleep(0.1)
				result.append(i)

		task.doTrading = countTo3
		task.startup()
		await task.waitFinished()
		self.assertEqual(result, [1, 2, 3])


	@asynciotest
	async def test_buyer_goodFlow(self):
		storage = MockStorage(self, startCount=42)

		orderID = ordertask.BuyOrder.create(storage, 2, 1234)
		order = ordertask.BuyOrder(storage, orderID, 'lnAddress')

		outgoingMessages = asyncio.Queue()

		def handleOutgoingMessage(msg):
			outgoingMessages.put_nowait(msg)
		client = Mock()
		client.handleOutgoingMessage = handleOutgoingMessage

		task = ordertask.OrderTask(client, storage, order)
		task.startup()

		remainingAmount = order.amount
		for txAmount in [1000, 234]:
			storage.reset(startCount=43) #clean up from previous iteration
			order.setAmount = Mock() #Replace mock object with a fresh one

			#Offer gets published
			msg = await outgoingMessages.get()
			self.assertEqual(msg, messages.BL4PAddOffer(
				localOrderID=42,

				offer=order,
				))
			task.setCallResult(messages.BL4PAddOfferResult(
				ID=6,
				))

			#TODO: is the next message in a race condition with the previous?
			await asyncio.sleep(0.1)

			#Incoming LN transaction arrives
			paymentPreimage = b'foo'
			paymentHash = sha256(paymentPreimage)
			task.setCallResult(messages.LNIncoming(
				fiatAmount=txAmount,
				cryptoAmount=500,
				paymentHash=paymentHash,
				))

			msg = await outgoingMessages.get()

			remainingAmount -= txAmount
			order.setAmount.assert_called_once_with(remainingAmount)
			order.amount = remainingAmount
			self.assertEqual(storage.buyTransactions, {43: {
				'ID': 43,
				'status': ordertask.STATUS_INITIAL,
				'buyOrder': 42,
				'fiatAmount': txAmount,
				'cryptoAmount': 500,
				'paymentHash': paymentHash,
				'paymentPreimage': None,
				}})

			#Funds get sent on BL4P
			self.assertEqual(msg, messages.BL4PSend(
				localOrderID=42,

				amount=txAmount,
				paymentHash=paymentHash,
				))
			task.setCallResult(messages.BL4PSendResult(
				paymentPreimage=paymentPreimage,
				))

			msg = await outgoingMessages.get()

			self.assertEqual(storage.buyTransactions, {43: {
				'ID': 43,
				'status': ordertask.STATUS_FINISHED,
				'buyOrder': 42,
				'fiatAmount': txAmount,
				'cryptoAmount': 500,
				'paymentHash': paymentHash,
				'paymentPreimage': paymentPreimage,
				}})

			#LN transaction gets finished
			self.assertEqual(msg, messages.LNFinish(
				paymentHash=paymentHash,
				paymentPreimage=paymentPreimage,
				))

			#Old offer gets removed
			msg = await outgoingMessages.get()
			self.assertEqual(msg, messages.BL4PRemoveOffer(
				localOrderID=42,

				offerID=6,
				))
			task.setCallResult(messages.BL4PRemoveOfferResult(
				))

		await task.waitFinished()


	@asynciotest
	async def test_continueBuyTransaction(self):
		storage = MockStorage(self, startCount=42)

		orderID = ordertask.BuyOrder.create(storage,
			190000,   #mCent / BTC = 1.9 EUR/BTC
			123400000 #mCent    = 1234 EUR
			)
		order = ordertask.BuyOrder(storage, orderID, 'buyerAddress')

		outgoingMessages = asyncio.Queue()

		def handleOutgoingMessage(msg):
			outgoingMessages.put_nowait(msg)
		client = Mock()
		client.handleOutgoingMessage = handleOutgoingMessage

		storage.buyTransactions = \
		{
		41:
			{
			'ID': 41,
			'buyOrder': orderID,
			'status': 0,

			'fiatAmount': 100000000,

			'paymentHash': b'foo',
			}
		}

		task = ordertask.OrderTask(client, storage, order)
		task.startup()

		msg = await outgoingMessages.get()
		self.assertEqual(msg, messages.BL4PSend(
			localOrderID=42,

			amount = 100000000,
			paymentHash = b'foo',
			))

		await task.shutdown()

		#Database inconsistency exception:
		storage.buyTransactions = \
		{
		41:
			{
			'ID': 41,
			'buyOrder': orderID,
			'status': 4,
			}
		}

		task = ordertask.OrderTask(client, storage, order)
		with self.assertRaises(Exception):
			await task.continueBuyTransaction()


	@asynciotest
	async def test_seller_goodFlow(self):
		storage = MockStorage(self, startCount=42)

		orderID = ordertask.SellOrder.create(storage,
			190000,         #mCent / BTC = 1.9 EUR/BTC
			123400000000000 #mSatoshi    = 1234 BTC
			)
		order = ordertask.SellOrder(storage, orderID, 'sellerAddress')

		outgoingMessages = asyncio.Queue()

		def handleOutgoingMessage(msg):
			outgoingMessages.put_nowait(msg)
		client = Mock()
		client.handleOutgoingMessage = handleOutgoingMessage

		task = ordertask.OrderTask(client, storage, order)
		task.startup()

		o1 = Mock()
		o1.getConditionMin = Mock(return_value=23)
		o1.getConditionMax = Mock(return_value=53)
		toPB2_return = Mock()
		toPB2_return.SerializeToString = Mock(return_value=b'bar')
		o1.toPB2 = Mock(return_value=toPB2_return)
		o1.ask.max_amount = 1000 #BTC
		o1.ask.max_amount_divisor = 1
		o1.bid.max_amount = 2000 #EUR
		o1.bid.max_amount_divisor = 1
		o1.ID = 6
		o1.address = 'buyerAddress'

		remainingAmount = order.amount
		for i in range(2):
			storage.reset(startCount=43) #clean up from previous iteration
			order.setAmount = Mock() #Replace mock object with a fresh one

			#Expected data:
			maxSenderCryptoAmount = \
			[
			105263157445776, #1052 BTC = 2000 EUR / seller limit rate
			22400000000000,  #224 BTC = 1234 BTC - 1010 BTC
			][i]
			senderCryptoAmount = \
			[
			101000000000000, #1010 BTC
			maxSenderCryptoAmount,
			][i]
			receiverCryptoAmount = \
			[
			100000000000000, #1000 BTC
			21280000500000,  #212.8 BTC = 425.6 BTC * buyer limit rate
			][i]
			senderFiatAmount = \
			[
			200000000, #2000 EUR
			42560001,  #425.6 EUR = 224 BTC * seller limit rate
			][i]
			receiverFiatAmount = \
			[
			190000000, #1900 EUR
			40000000,  #400 EUR
			][i]

			#Offers get found
			msg = await outgoingMessages.get()
			self.assertEqual(msg, messages.BL4PFindOffers(
				localOrderID=42,

				query=order,
				))
			task.setCallResult(messages.BL4PFindOffersResult(
				offers=[o1, Mock()],
				))

			msg = await outgoingMessages.get()

			#For now, behavior is to always select the first:
			self.assertEqual(task.counterOffer, o1)

			self.assertEqual(storage.counterOffers, {43:
				{
				'ID': 43,
				'blob': b'bar',
				}})
			self.assertEqual(storage.sellTransactions, {44:
				{
				'ID': 44,
				'sellOrder': 42,
				'counterOffer': 43,
				'status': 0,
				'senderTimeoutDelta': 100, #highest minimum
				'lockedTimeoutDelta': 53, #lowest maximum
				'CLTVExpiryDelta':    23, #highest minimum
				'maxSenderCryptoAmount': maxSenderCryptoAmount,
				'senderCryptoAmount': None,
				'receiverCryptoAmount': receiverCryptoAmount,
				'senderFiatAmount': senderFiatAmount,
				'receiverFiatAmount': None,
				'paymentHash': None,
				'paymentPreimage': None,
				}})

			#Transaction starts on BL4P
			paymentPreimage = b'foo'
			paymentHash = sha256(paymentPreimage)
			self.assertEqual(msg, messages.BL4PStart(
				localOrderID=42,

		                amount=senderFiatAmount,
		                sender_timeout_delta_ms=100,
		                locked_timeout_delta_s=53,
		                receiver_pays_fee=True,
				))
			task.setCallResult(messages.BL4PStartResult(
				senderAmount=senderFiatAmount,
				receiverAmount=receiverFiatAmount,
				paymentHash=paymentHash,
				))

			msg = await outgoingMessages.get()

			self.assertEqual(storage.sellTransactions, {44:
				{
				'ID': 44,
				'sellOrder': 42,
				'counterOffer': 43,
				'status': 1,
				'senderTimeoutDelta': 100,
				'lockedTimeoutDelta': 53,
				'CLTVExpiryDelta':    23,
				'maxSenderCryptoAmount': maxSenderCryptoAmount,
				'senderCryptoAmount': None,
				'receiverCryptoAmount': receiverCryptoAmount,
				'senderFiatAmount': senderFiatAmount,
				'receiverFiatAmount': receiverFiatAmount,
				'paymentHash': paymentHash,
				'paymentPreimage': None,
				}})

			#LN transaction gets performed
			self.assertEqual(msg, messages.LNPay(
				localOrderID=42,

				destinationNodeID     = 'buyerAddress',
				paymentHash           = paymentHash,
				recipientCryptoAmount = receiverCryptoAmount,
				maxSenderCryptoAmount = maxSenderCryptoAmount,
				minCLTVExpiryDelta    = 23,
				fiatAmount            = senderFiatAmount,
				offerID               = 6,
				))
			task.setCallResult(messages.LNPayResult(
				senderCryptoAmount=senderCryptoAmount,
				paymentPreimage=paymentPreimage,
				))

			msg = await outgoingMessages.get()

			self.assertEqual(storage.sellTransactions, {44:
				{
				'ID': 44,
				'sellOrder': 42,
				'counterOffer': 43,
				'status': 2,
				'senderTimeoutDelta': 100,
				'lockedTimeoutDelta': 53,
				'CLTVExpiryDelta':    23,
				'maxSenderCryptoAmount': maxSenderCryptoAmount,
				'senderCryptoAmount': senderCryptoAmount,
				'receiverCryptoAmount': receiverCryptoAmount,
				'senderFiatAmount': senderFiatAmount,
				'receiverFiatAmount': receiverFiatAmount,
				'paymentHash': paymentHash,
				'paymentPreimage': paymentPreimage,
				}})
			remainingAmount -= senderCryptoAmount
			order.setAmount.assert_called_once_with(remainingAmount)
			order.amount = remainingAmount
			order.updateOfferMaxAmounts()

			#Funds get received on BL4P
			self.assertEqual(msg, messages.BL4PReceive(
				localOrderID=42,

				paymentPreimage=paymentPreimage,
				))
			task.setCallResult(messages.BL4PReceiveResult(
				))

			await asyncio.sleep(0.1)

			self.assertEqual(storage.sellTransactions, {44:
				{
				'ID': 44,
				'sellOrder': 42,
				'counterOffer': 43,
				'status': 3,
				'senderTimeoutDelta': 100,
				'lockedTimeoutDelta': 53,
				'CLTVExpiryDelta':    23,
				'maxSenderCryptoAmount': maxSenderCryptoAmount,
				'senderCryptoAmount': senderCryptoAmount,
				'receiverCryptoAmount': receiverCryptoAmount,
				'senderFiatAmount': senderFiatAmount,
				'receiverFiatAmount': receiverFiatAmount,
				'paymentHash': paymentHash,
				'paymentPreimage': paymentPreimage,
				}})

		await task.waitFinished()


	@asynciotest
	async def test_continueSellTransaction(self):
		storage = MockStorage(self, startCount=42)

		orderID = ordertask.SellOrder.create(storage,
			190000,         #mCent / BTC = 1.9 EUR/BTC
			123400000000000 #mSatoshi    = 1234 BTC
			)
		order = ordertask.SellOrder(storage, orderID, 'sellerAddress')

		ID = ordertask.BuyOrder.create(storage,
			210000,         #mCent / BTC = 2.1 EUR/BTC
			100000          #mCent       = 1000 EUR
			)

		originalCounterOffer = ordertask.BuyOrder(storage, ID, 'buyerAddress')
		storage.counterOffers = \
		{40:
			{
			'ID': 40,
			'blob': originalCounterOffer.toPB2().SerializeToString()
			}
		}

		outgoingMessages = asyncio.Queue()

		def handleOutgoingMessage(msg):
			outgoingMessages.put_nowait(msg)
		client = Mock()
		client.handleOutgoingMessage = handleOutgoingMessage

		#status -> message:
		expectedMessages = \
		{
		0: messages.BL4PStart(
				localOrderID=42,

				amount = 1200,
				sender_timeout_delta_ms = 34,
				locked_timeout_delta_s = 56,
				receiver_pays_fee = True,
				),
		1: messages.LNPay(
				localOrderID=42,

		                destinationNodeID     = 'buyerAddress',
		                offerID               = 43,

		                recipientCryptoAmount = 10000,
		                maxSenderCryptoAmount = 11000,
		                fiatAmount            = 1200,

		                minCLTVExpiryDelta    = 78,

		                paymentHash           = b'foo',
				),
		2: messages.BL4PReceive(
				localOrderID=42,

				paymentPreimage = b'bar',
				),
		}

		for status, expectedMessage in expectedMessages.items():
			storage.sellTransactions = \
			{
			41:
				{
				'ID': 41,
				'sellOrder': orderID,
				'counterOffer': 40,
				'status': status,

				'senderFiatAmount': 1200,
				'receiverCryptoAmount': 10000,
				'maxSenderCryptoAmount': 11000,

				'senderTimeoutDelta': 34,
				'lockedTimeoutDelta': 56,
				'CLTVExpiryDelta'   : 78,

				'paymentHash': b'foo',
				'paymentPreimage': b'bar',
				}
			}

			task = ordertask.OrderTask(client, storage, order)
			task.startup()

			msg = await outgoingMessages.get()
			self.assertEqual(msg, expectedMessage)

			await task.shutdown()

		#Database inconsistency exception:
		storage.sellTransactions = \
		{
		41:
			{
			'ID': 41,
			'sellOrder': orderID,
			'counterOffer': 40,
			'status': 4,
			}
		}

		task = ordertask.OrderTask(client, storage, order)
		with self.assertRaises(Exception):
			await task.continueSellTransaction()


	@asynciotest
	async def test_setCallResult_exceptions(self):
		task = ordertask.OrderTask(None, None, None)
		with self.assertRaises(ordertask.UnexpectedResult):
			task.setCallResult(3.0)

		waitTask = asyncio.ensure_future(task.waitForIncomingMessage(int))
		await asyncio.sleep(0.1)

		with self.assertRaises(ordertask.UnexpectedResult):
			task.setCallResult(3.0)

		task.setCallResult(6)

		value = await waitTask
		self.assertEqual(value, 6)


	@asynciotest
	async def test_doTrading_exceptions(self):
		#Unsupported order type:
		task = ordertask.OrderTask(None, None, None)
		with patch.object(ordertask, 'logException', Mock()) as logException:
			with self.assertRaises(Exception):
				await task.doTrading()
			logException.assert_called_once_with()

		#Canceled exception:
		storage = MockStorage(self, startCount=42)
		orderID = ordertask.BuyOrder.create(storage, 2, 1234)
		order = ordertask.BuyOrder(storage, orderID, 'lnAddress')
		task = ordertask.OrderTask(Mock(), None, order)

		async def continueBuyTransaction():
			raise asyncio.CancelledError()

		with patch.object(task, 'continueBuyTransaction', continueBuyTransaction):
			#No exception:
			await task.doTrading()


	@asynciotest
	async def test_doOfferSearch_loop(self):
		outgoingMessages = asyncio.Queue()

		def handleOutgoingMessage(msg):
			outgoingMessages.put_nowait(msg)
		client = Mock()
		client.handleOutgoingMessage = handleOutgoingMessage

		order = Mock()
		order.ID = 42
		order.remoteOfferID = None
		task = ordertask.OrderTask(client, None, order)

		done = []
		async def doTransaction():
			self.assertEqual(done, [])
			done.append(True)
		task.doTransaction = doTransaction

		searchTask = asyncio.ensure_future(task.doOfferSearch())

		#No results:
		msg = await outgoingMessages.get()
		self.assertEqual(msg, messages.BL4PFindOffers(
			localOrderID=42,

			query=order,
			))
		task.setCallResult(messages.BL4PFindOffersResult(
			offers = [],
			))

		#Offer gets published:
		msg = await outgoingMessages.get()
		self.assertEqual(msg, messages.BL4PAddOffer(
			localOrderID=42,

			offer=order,
			))
		task.setCallResult(messages.BL4PAddOfferResult(
			ID = 6,
			))

		#No results again:
		t0 = time.time()
		msg = await outgoingMessages.get()
		t1 = time.time()
		self.assertAlmostEqual(t1-t0, 1.0, places=2)
		self.assertEqual(msg, messages.BL4PFindOffers(
			localOrderID=42,

			query=order,
			))
		task.setCallResult(messages.BL4PFindOffersResult(
			offers = [],
			))
		self.assertEqual(order.remoteOfferID, 6)

		#Multiple results:
		msg = await outgoingMessages.get()
		self.assertEqual(msg, messages.BL4PFindOffers(
			localOrderID=42,

			query=order,
			))
		task.setCallResult(messages.BL4PFindOffersResult(
			offers = ['foo', 'bar'],
			))

		await searchTask

		self.assertEqual(done, [True])
		self.assertEqual(task.counterOffer, 'foo')



if __name__ == '__main__':
	unittest.main(verbosity=2)

