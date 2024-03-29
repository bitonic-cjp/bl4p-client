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
import hashlib
import logging
import sys
import time
import unittest
from unittest.mock import patch, Mock

from utils import asynciotest, MockCursor, MockStorage

sys.path.append('..')

from bl4p_api import offer
import messages
from order import Order, ORDER_STATUS_CANCEL_REQUESTED, ORDER_STATUS_CANCELED
import ordertask



sha256 = lambda preimage: hashlib.sha256(preimage).digest() 



class TestOrderTask(unittest.TestCase):
	def setUp(self):
		self.storage = MockStorage(test=self, startCount=42)

		self.outgoingMessages = asyncio.Queue()

		def handleOutgoingMessage(msg):
			self.outgoingMessages.put_nowait(msg)
		self.client = Mock()
		self.client.handleOutgoingMessage = handleOutgoingMessage


	async def shutdownOrderTask(self, task):
		#While we await for task.shutdown, the task calls BL4P to remove the
		#offer; it then awaits for the result.
		#However, we can't give it the result since we're awaiting shutdown.
		#To work around this, we patch the waitForIncomingMessage method, so
		#that the task receives the message it expects once it starts waiting
		#for it.

		async def waitForIncomingMessage(expectedResultType):
			self.assertEqual(expectedResultType, messages.BL4PRemoveOfferResult)
			return messages.BL4PRemoveOfferResult(request = None)

		with patch.object(task, 'waitForIncomingMessage', waitForIncomingMessage):
			await task.shutdown()

		msg = await self.outgoingMessages.get()
		self.assertEqual(msg, messages.BL4PRemoveOffer(
			localOrderID=42,

			offerID=6,
			))


	@asynciotest
	async def test_waitForBL4PConnection(self):
		self.client.isBL4PConnected = Mock(return_value=True)
		task = ordertask.OrderTask(self.client, self.storage, None)
		await task.waitForBL4PConnection()
		self.client.isBL4PConnected.assert_called_with()

		self.client.isBL4PConnected = Mock(return_value=False)
		calls = []
		async def waitForBL4PConnection():
			calls.append(None)
		self.client.waitForBL4PConnection = waitForBL4PConnection
		task = ordertask.OrderTask(self.client, self.storage, None)
		await task.waitForBL4PConnection()
		self.client.isBL4PConnected.assert_called_with()
		self.assertEqual(len(calls), 1)


	def test_BuyTransaction(self):
		with patch.object(ordertask.StoredObject, 'createStoredObject', Mock(return_value=43)):
			self.assertEqual(ordertask.BuyTransaction.create('foo', 'baa', 'bab', 'bac', 'bad'), 43)

			ordertask.StoredObject.createStoredObject.assert_called_once_with(
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
		with patch.object(ordertask.StoredObject, 'createStoredObject', Mock(return_value=43)):
			self.assertEqual(ordertask.SellTransaction.create('foo', 'baa', 'bab', 'bac', 'bae', 'baf', 'bag', 'bah'), 43)

			ordertask.StoredObject.createStoredObject.assert_called_once_with(
				'foo', 'sellTransactions',
				sellOrder='baa', counterOffer='bab', buyerFiatAmount='bac', buyerCryptoAmount='bae', senderTimeoutDelta='baf', lockedTimeoutDelta='bag', CLTVExpiryDelta='bah',
				status=0, sellerFiatAmount=None, sellerCryptoAmount=None, paymentHash=None, paymentPreimage=None,
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
		with patch.object(ordertask.StoredObject, 'createStoredObject', Mock(return_value=43)):
			PB2 = Mock()
			PB2.SerializeToString = Mock(return_value=b'bar')
			counterOffer = Mock()
			counterOffer.toPB2 = Mock(return_value=PB2)

			self.assertEqual(ordertask.CounterOffer.create('foo', counterOffer), 43)

			ordertask.StoredObject.createStoredObject.assert_called_once_with(
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


	def test_cancel(self):
		orderID = ordertask.BuyOrder.create(self.storage,
			190000,   #mCent / BTC = 1.9 EUR/BTC
			123400000 #mCent    = 1234 EUR
			)
		order = ordertask.BuyOrder(self.storage, orderID, 'lnAddress')
		task = ordertask.OrderTask(self.client, self.storage, order)
		task.task = Mock()
		task.cancel()
		self.assertEqual(order.status, ORDER_STATUS_CANCELED)
		task.task.cancel.assert_called_with()

		task.transaction = Mock()
		task.cancel()
		self.assertEqual(order.status, ORDER_STATUS_CANCEL_REQUESTED)


	def test_getListInfo(self):
		orderID = ordertask.BuyOrder.create(self.storage,
			190000,   #mCent / BTC = 1.9 EUR/BTC
			123400000 #mCent    = 1234 EUR
			)
		order = ordertask.BuyOrder(self.storage, orderID, 'lnAddress')
		task = ordertask.OrderTask(self.client, self.storage, order)

		self.assertEqual(task.getListInfo(),
			{
			'ID': orderID,
			'status': 'active',
			'limitRate': 190000,
			'amount': 123400000,
			})

		txID = task.transaction = ordertask.BuyTransaction.create(
			self.storage,
			buyOrder = orderID,
			fiatAmount = 12,
			cryptoAmount = 34,
			paymentHash = b'foobar'
			)
		task.transaction = ordertask.BuyTransaction(self.storage, txID)
		self.assertEqual(task.getListInfo(),
			{
			'ID': orderID,
			'status': 'active',
			'limitRate': 190000,
			'amount': 123400000,
			'transaction':
				{
				'status': 'initial',
				'fiatAmount': 12,
				'cryptoAmount': 34,
				}
			})		

		txID = task.transaction = ordertask.SellTransaction.create(
			self.storage,
			sellOrder = orderID,
			counterOffer = 0,
			buyerFiatAmount = 12,
			buyerCryptoAmount = 56,
			senderTimeoutDelta = 0,
			lockedTimeoutDelta = 0,
			CLTVExpiryDelta = 0,
			)
		task.transaction = ordertask.SellTransaction(self.storage, txID)
		task.transaction.sellerFiatAmount = 34
		task.transaction.sellerCryptoAmount = 78
		self.assertEqual(task.getListInfo(),
			{
			'ID': orderID,
			'status': 'active',
			'limitRate': 190000,
			'amount': 123400000,
			'transaction':
				{
				'status': 'initial',
				'buyerFiatAmount': 12,
				'sellerFiatAmount': 34,
				'buyerCryptoAmount': 56,
				'sellerCryptoAmount': 78,
				}
			})		


	@asynciotest
	async def test_buyer_goodFlow(self):
		orderID = ordertask.BuyOrder.create(self.storage,
			190000,   #mCent / BTC = 1.9 EUR/BTC
			123400000 #mCent    = 1234 EUR
			)
		order = ordertask.BuyOrder(self.storage, orderID, 'lnAddress')

		task = ordertask.OrderTask(self.client, self.storage, order)
		task.startup()

		remainingAmount = order.amount
		for txAmount in [100000000, 23400000]:
			self.storage.reset(startCount=43) #clean up from previous iteration
			self.storage.buyOrders[orderID] = {}
			order.setAmount = Mock() #Replace mock object with a fresh one

			#Offer gets published
			msg = await self.outgoingMessages.get()
			self.assertEqual(msg, messages.BL4PAddOffer(
				localOrderID=42,

				offer=order,
				))
			task.setCallResult(messages.BL4PAddOfferResult(
				request=None,
				ID=6,
				))

			#TODO: is the next message in a race condition with the previous?
			await asyncio.sleep(0.1)

			#Incoming LN transaction arrives
			paymentPreimage = b'foo'
			paymentHash = sha256(paymentPreimage)
			task.setCallResult(messages.LNIncoming(
				offerID=42,
				CLTVExpiryDelta=0,
				fiatAmount=txAmount,
				cryptoAmount=100000000000000,
				paymentHash=paymentHash,
				))

			msg = await self.outgoingMessages.get()

			remainingAmount -= txAmount
			order.setAmount.assert_called_once_with(remainingAmount)
			order.amount = remainingAmount
			self.assertEqual(self.storage.buyTransactions, {43: {
				'ID': 43,
				'status': ordertask.TX_STATUS_INITIAL,
				'buyOrder': 42,
				'fiatAmount': txAmount,
				'cryptoAmount': 100000000000000,
				'paymentHash': paymentHash,
				'paymentPreimage': None,
				}})

			#Funds get sent on BL4P
			self.assertEqual(msg, messages.BL4PSend(
				localOrderID=42,

				amount=txAmount,
				paymentHash=paymentHash,
				max_locked_timeout_delta_s = 3600*24*14,
				selfReport = \
					{
					'paymentHash'         : paymentHash.hex(),
					'offerID'             : str(orderID),
					'receiverCryptoAmount': '1000.00000000000',
					'cryptoCurrency'      : 'btc',
					},
				))
			task.setCallResult(messages.BL4PSendResult(
				request=None,
				paymentPreimage=paymentPreimage,
				))

			msg = await self.outgoingMessages.get()

			self.assertEqual(self.storage.buyTransactions, {43: {
				'ID': 43,
				'status': ordertask.TX_STATUS_FINISHED,
				'buyOrder': 42,
				'fiatAmount': txAmount,
				'cryptoAmount': 100000000000000,
				'paymentHash': paymentHash,
				'paymentPreimage': paymentPreimage,
				}})
			self.assertEqual(task.transaction, None)

			#LN transaction gets finished
			self.assertEqual(msg, messages.LNFinish(
				paymentHash=paymentHash,
				paymentPreimage=paymentPreimage,
				))

			#Old offer gets removed
			msg = await self.outgoingMessages.get()
			self.assertEqual(msg, messages.BL4PRemoveOffer(
				localOrderID=42,

				offerID=6,
				))
			task.setCallResult(messages.BL4PRemoveOfferResult(
				request=None,
				))

		await task.waitFinished()

		self.assertEqual(self.storage.buyOrders[orderID]['status'], 1) #completed


	@asynciotest
	async def test_refusedBuyTransaction(self):
		orderID = ordertask.BuyOrder.create(self.storage,
			190000,   #mCent / BTC = 1.9 EUR/BTC
			123400000 #mCent    = 1234 EUR
			)
		order = ordertask.BuyOrder(self.storage, orderID, 'lnAddress')

		task = ordertask.OrderTask(self.client, self.storage, order)
		task.startup()

		self.storage.reset(startCount=43) #clean up from previous iteration
		self.storage.buyOrders[orderID] = {}
		order.setAmount = Mock() #Replace mock object with a fresh one

		#Offer gets published
		msg = await self.outgoingMessages.get()
		self.assertEqual(msg, messages.BL4PAddOffer(
			localOrderID=42,

			offer=order,
			))
		task.setCallResult(messages.BL4PAddOfferResult(
			request=None,
			ID=6,
			))

		#TODO: is the next message in a race condition with the previous?
		await asyncio.sleep(0.1)

		#Incoming LN transaction arrives
		paymentPreimage = b'foo'
		paymentHash = sha256(paymentPreimage)
		task.setCallResult(messages.LNIncoming(
			offerID=42,
			CLTVExpiryDelta=0,
			fiatAmount=100000000, #mCent = 1000 EUR
			cryptoAmount=50,      #mBTC = 0.00000000050 BTC
			paymentHash=paymentHash,
			))

		msg = await self.outgoingMessages.get()

		await self.shutdownOrderTask(task)


	@asynciotest
	async def test_continueBuyTransaction(self):
		orderID = ordertask.BuyOrder.create(self.storage,
			190000,   #mCent / BTC = 1.9 EUR/BTC
			123400000 #mCent    = 1234 EUR
			)
		order = ordertask.BuyOrder(self.storage, orderID, 'buyerAddress')

		self.storage.buyTransactions = \
		{
		41:
			{
			'ID': 41,
			'buyOrder': orderID,
			'status': 0,

			'fiatAmount': 100000000,
			'cryptoAmount': 200000000,

			'paymentHash': b'foo',
			}
		}

		task = ordertask.OrderTask(self.client, self.storage, order)
		task.startup()

		await asyncio.sleep(0.1)

		task.setCallResult(messages.LNIncoming(
			offerID=42,
			CLTVExpiryDelta=0,
			fiatAmount=100000000,
			cryptoAmount=200000000,
			paymentHash=b'foo',
			))

		msg = await self.outgoingMessages.get()
		self.assertEqual(msg, messages.BL4PSend(
			localOrderID=42,

			amount = 100000000,
			paymentHash = b'foo',
			max_locked_timeout_delta_s = 3600*24*14,
			selfReport = \
				{
				'paymentHash'         : '666f6f', #foo in hex
				'offerID'             : str(orderID),
				'receiverCryptoAmount': '0.00200000000',
				'cryptoCurrency'      : 'btc',
				},
			))

		await task.shutdown()

		#Database inconsistency exception:
		self.storage.buyTransactions = \
		{
		41:
			{
			'ID': 41,
			'buyOrder': orderID,
			'status': 100,
			}
		}

		task = ordertask.OrderTask(self.client, self.storage, order)
		with self.assertRaises(Exception):
			await task.continueBuyTransaction()


	@asynciotest
	async def test_failedBuyTransaction(self):
		orderID = ordertask.BuyOrder.create(self.storage,
			190000,   #mCent / BTC = 1.9 EUR/BTC
			123400000 #mCent    = 1234 EUR
			)
		order = ordertask.BuyOrder(self.storage, orderID, 'buyerAddress')
		order.remoteOfferID = 6
		order.setAmount = Mock()

		self.storage.buyTransactions = \
		{
		41:
			{
			'ID': 41,
			'buyOrder': orderID,
			'status': 0,
			'fiatAmount': 100000000,
			'cryptoAmount': 200000000,
			'paymentHash': b'foo',
			}
		}

		task = ordertask.OrderTask(self.client, self.storage, order)
		task.startup()

		await asyncio.sleep(0.1)

		task.setCallResult(messages.LNIncoming(
			offerID=42,
			CLTVExpiryDelta=0,
			fiatAmount=100000000,
			cryptoAmount=200000000,
			paymentHash=b'foo',
			))

		msg = await self.outgoingMessages.get()
		self.assertEqual(msg, messages.BL4PSend(
			localOrderID=42,

			amount = 100000000,
			paymentHash = b'foo',
			max_locked_timeout_delta_s = 3600*24*14,
			selfReport = \
				{
				'paymentHash'         : '666f6f', #foo in hex
				'offerID'             : str(orderID),
				'receiverCryptoAmount': '0.00200000000',
				'cryptoCurrency'      : 'btc',
				},
			))
		task.setCallResult(messages.BL4PError(
			request = None,
			))

		#LN transaction gets canceled
		msg = await self.outgoingMessages.get()
		self.assertEqual(msg, messages.LNFail(
			paymentHash = b'foo',
			))

		order.setAmount.assert_called_once_with(223400000)
		self.assertEqual(self.storage.buyTransactions, {41: {
			'ID': 41,
			'status': ordertask.TX_STATUS_CANCELED,
			'buyOrder': orderID,
			'fiatAmount': 100000000,
			'cryptoAmount': 200000000,
			'paymentHash': b'foo',
			}})
		self.assertEqual(task.transaction, None)

		#Old offer gets removed
		msg = await self.outgoingMessages.get()
		self.assertTrue(isinstance(msg, messages.BL4PRemoveOffer))
		task.setCallResult(messages.BL4PRemoveOfferResult(
			request = None,
			))

		#New offer gets added
		msg = await self.outgoingMessages.get()
		self.assertTrue(isinstance(msg, messages.BL4PAddOffer))
		task.setCallResult(messages.BL4PAddOfferResult(
			request = None,
			ID = 6,
			))

		#Continues to next iteration:
		await asyncio.sleep(0.1)

		await self.shutdownOrderTask(task)


	@asynciotest
	async def test_buyer_repeatFinishedTransaction(self):
		orderID = ordertask.BuyOrder.create(self.storage,
			190000,   #mCent / BTC = 1.9 EUR/BTC
			123400000 #mCent    = 1234 EUR
			)
		order = ordertask.BuyOrder(self.storage, orderID, 'buyerAddress')
		order.remoteOfferID = 6
		order.setAmount = Mock()

		self.storage.buyTransactions = \
		{
		41:
			{
			'ID': 41,
			'buyOrder': orderID,
			'status': 4, #finished
			'fiatAmount': 100000000,
			'cryptoAmount': 200000000,
			'paymentHash': b'foo',
			'paymentPreimage': b'bar',
			},
		42:
			{
			'ID': 42,
			'buyOrder': orderID,
			'status': 0,
			'fiatAmount': 300000000,
			'cryptoAmount': 600000000,
			'paymentHash': b'foo2',
			}
		}

		task = ordertask.OrderTask(self.client, self.storage, order)
		task.startup()

		await asyncio.sleep(0.1)

		task.setCallResult(messages.LNIncoming(
			offerID=42,
			CLTVExpiryDelta=0,
			fiatAmount=100000000,
			cryptoAmount=200000000,
			paymentHash=b'foo',
			))

		msg = await self.outgoingMessages.get()
		self.assertEqual(msg, messages.LNFinish(
			paymentHash     = b'foo',
			paymentPreimage = b'bar'
			))

		await self.shutdownOrderTask(task)


	@asynciotest
	async def test_buyer_repeatCanceledTransaction(self):
		orderID = ordertask.BuyOrder.create(self.storage,
			190000,   #mCent / BTC = 1.9 EUR/BTC
			123400000 #mCent    = 1234 EUR
			)
		order = ordertask.BuyOrder(self.storage, orderID, 'buyerAddress')
		order.remoteOfferID = 6
		order.setAmount = Mock()

		self.storage.buyTransactions = \
		{
		41:
			{
			'ID': 41,
			'buyOrder': orderID,
			'status': 5, #canceled
			'fiatAmount': 100000000,
			'cryptoAmount': 200000000,
			'paymentHash': b'foo',
			},
		42:
			{
			'ID': 42,
			'buyOrder': orderID,
			'status': 0,
			'fiatAmount': 300000000,
			'cryptoAmount': 600000000,
			'paymentHash': b'foo2',
			}
		}

		task = ordertask.OrderTask(self.client, self.storage, order)
		task.startup()

		await asyncio.sleep(0.1)

		task.setCallResult(messages.LNIncoming(
			offerID=42,
			CLTVExpiryDelta=0,
			fiatAmount=100000000,
			cryptoAmount=200000000,
			paymentHash=b'foo',
			))

		msg = await self.outgoingMessages.get()
		self.assertEqual(msg, messages.LNFail(
			paymentHash     = b'foo',
			))

		await self.shutdownOrderTask(task)


	@asynciotest
	async def test_seller_goodFlow(self):
		orderID = ordertask.SellOrder.create(self.storage,
			190000,         #mCent / BTC = 1.9 EUR/BTC
			123400000000000 #mSatoshi    = 1234 BTC
			)
		order = ordertask.SellOrder(self.storage, orderID, 'sellerAddress')

		task = ordertask.OrderTask(self.client, self.storage, order)
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

		#We're going to match the sell order (order) twice with the
		#counter-offer (o1).

		remainingAmount = order.amount
		for i in range(2):
			self.storage.reset(startCount=43) #clean up from previous iteration
			self.storage.sellOrders[orderID] = {}
			order.setAmount = Mock() #Replace mock object with a fresh one

			#Expected data:
			buyerCryptoAmount = \
			[
			100000000000000, #1000 BTC = min(1234, 1000)
			22900000000000,  # 229 BTC = min(1234 - 1005, 1000)
			][i]
			buyerFiatAmount = \
			[
			200000000, #2000 EUR = 1000 BTC * buyer limit rate
			45800000,  #458 EUR  =  229 BTC * buyer limit rate
			][i]
			minSellerFiatAmount = \
			[
			190000000, #1900   EUR = 1000 BTC * seller limit rate
			 43510000, # 435.1 EUR =  229 BTC * seller limit rate
			][i]
			maxSellerCryptoAmount = \
			[
			101000000000000, #1010    BTC = 1.01 * 1000 BTC
			 23129000000000, # 231.29 BTC = 1.01 *  229 BTC
			][i]
			sellerCryptoAmount = \
			[
			100500000000000, #1005 BTC, just slightly more than nominalCryptoAmount
			 23500000000000, # 235 BTC, just slightly more than nominalCryptoAmount
			][i]
			buyerCryptoAmount_str = \
			[
			'1000.00000000000', #1000 BTC, Equals the nominal amount
			'229.00000000000',  # 229 BTC, Equals the nominal amount
			][i]
			sellerFiatAmount = \
			[
			199000000, #1990 EUR, just slightly less than nominalFiatAmount
			45000000,  # 450 EUR, just slightly less than nominalFiatAmount
			][i]

			#Offers get found
			msg = await self.outgoingMessages.get()
			self.assertEqual(msg, messages.BL4PFindOffers(
				localOrderID=42,

				query=order,
				))
			task.setCallResult(messages.BL4PFindOffersResult(
				request=None,
				offers=[o1, Mock()],
				))

			msg = await self.outgoingMessages.get()

			#For now, behavior is to always select the first:
			self.assertEqual(task.counterOffer, o1)

			self.assertEqual(self.storage.counterOffers, {43:
				{
				'ID': 43,
				'blob': b'bar',
				}})
			self.assertEqual(self.storage.sellTransactions, {44:
				{
				'ID': 44,
				'sellOrder': 42,
				'counterOffer': 43,
				'status': 0,
				'senderTimeoutDelta': 2000, #highest minimum
				'lockedTimeoutDelta': 53, #lowest maximum
				'CLTVExpiryDelta':    23, #highest minimum
				'buyerCryptoAmount': buyerCryptoAmount,
				'sellerCryptoAmount': None,
				'buyerFiatAmount': buyerFiatAmount,
				'sellerFiatAmount': None,
				'paymentHash': None,
				'paymentPreimage': None,
				}})

			#Transaction starts on BL4P
			paymentPreimage = b'foo'
			paymentHash = sha256(paymentPreimage)
			self.assertEqual(msg, messages.BL4PStart(
				localOrderID=42,

		                amount=buyerFiatAmount,
		                sender_timeout_delta_ms=2000,
		                locked_timeout_delta_s=53,
		                receiver_pays_fee=True,
				))
			task.setCallResult(messages.BL4PStartResult(
				request=None,
				senderAmount=buyerFiatAmount,
				receiverAmount=sellerFiatAmount,
				paymentHash=paymentHash,
				))

			msg = await self.outgoingMessages.get()

			self.assertEqual(self.storage.sellTransactions, {44:
				{
				'ID': 44,
				'sellOrder': 42,
				'counterOffer': 43,
				'status': ordertask.TX_STATUS_STARTED,
				'senderTimeoutDelta': 2000,
				'lockedTimeoutDelta': 53,
				'CLTVExpiryDelta':    23,
				'buyerCryptoAmount': buyerCryptoAmount,
				'sellerCryptoAmount': None,
				'buyerFiatAmount': buyerFiatAmount,
				'sellerFiatAmount': sellerFiatAmount,
				'paymentHash': paymentHash,
				'paymentPreimage': None,
				}})

			#Self-reporting on BL4P
			self.assertEqual(msg, messages.BL4PSelfReport(
				localOrderID=42,

				selfReport=\
					{
					'paymentHash'         : paymentHash.hex(),
					'offerID'             : str(o1.ID),
					'receiverCryptoAmount': buyerCryptoAmount_str,
					'cryptoCurrency'      : 'btc',
					},
				))
			task.setCallResult(messages.BL4PSelfReportResult(
				request=None,
				))

			msg = await self.outgoingMessages.get()

			self.assertEqual(self.storage.sellTransactions, {44:
				{
				'ID': 44,
				'sellOrder': 42,
				'counterOffer': 43,
				'status': ordertask.TX_STATUS_LOCKED,
				'senderTimeoutDelta': 2000,
				'lockedTimeoutDelta': 53,
				'CLTVExpiryDelta':    23,
				'buyerCryptoAmount': buyerCryptoAmount,
				'sellerCryptoAmount': None,
				'buyerFiatAmount': buyerFiatAmount,
				'sellerFiatAmount': sellerFiatAmount,
				'paymentHash': paymentHash,
				'paymentPreimage': None,
				}})

			#LN transaction gets performed
			self.assertEqual(msg, messages.LNPay(
				localOrderID=42,

				destinationNodeID     = 'buyerAddress',
				paymentHash           = paymentHash,
				recipientCryptoAmount = buyerCryptoAmount,
				maxSenderCryptoAmount = maxSellerCryptoAmount,
				minCLTVExpiryDelta    = 23,
				fiatAmount            = buyerFiatAmount,
				offerID               = 6,
				))
			task.setCallResult(messages.LNPayResult(
				localOrderID=44,
				paymentHash=paymentHash,
				senderCryptoAmount=sellerCryptoAmount,
				paymentPreimage=paymentPreimage,
				))

			msg = await self.outgoingMessages.get()

			self.assertEqual(self.storage.sellTransactions, {44:
				{
				'ID': 44,
				'sellOrder': 42,
				'counterOffer': 43,
				'status': ordertask.TX_STATUS_RECEIVED_PREIMAGE,
				'senderTimeoutDelta': 2000,
				'lockedTimeoutDelta': 53,
				'CLTVExpiryDelta':    23,
				'buyerCryptoAmount': buyerCryptoAmount,
				'sellerCryptoAmount': sellerCryptoAmount,
				'buyerFiatAmount': buyerFiatAmount,
				'sellerFiatAmount': sellerFiatAmount,
				'paymentHash': paymentHash,
				'paymentPreimage': paymentPreimage,
				}})
			remainingAmount -= sellerCryptoAmount
			if remainingAmount < 0 :
				remainingAmount = 0
			order.setAmount.assert_called_once_with(remainingAmount)
			order.amount = remainingAmount
			order.updateOfferMaxAmounts()

			#Funds get received on BL4P
			self.assertEqual(msg, messages.BL4PReceive(
				localOrderID=42,

				paymentPreimage=paymentPreimage,
				))
			task.setCallResult(messages.BL4PReceiveResult(
				request=None,
				))

			await asyncio.sleep(0.1)

			self.assertEqual(self.storage.sellTransactions, {44:
				{
				'ID': 44,
				'sellOrder': 42,
				'counterOffer': 43,
				'status': ordertask.TX_STATUS_FINISHED,
				'senderTimeoutDelta': 2000,
				'lockedTimeoutDelta': 53,
				'CLTVExpiryDelta':    23,
				'buyerCryptoAmount': buyerCryptoAmount,
				'sellerCryptoAmount': sellerCryptoAmount,
				'buyerFiatAmount': buyerFiatAmount,
				'sellerFiatAmount': sellerFiatAmount,
				'paymentHash': paymentHash,
				'paymentPreimage': paymentPreimage,
				}})
			self.assertEqual(task.transaction, None)

		await task.waitFinished()

		self.assertEqual(self.storage.sellOrders[orderID]['status'], 1) #completed


	@asynciotest
	async def test_continueSellTransaction(self):
		orderID = ordertask.SellOrder.create(self.storage,
			190000,         #mCent / BTC = 1.9 EUR/BTC
			123400000000000 #mSatoshi    = 1234 BTC
			)
		order = ordertask.SellOrder(self.storage, orderID, 'sellerAddress')

		ID = ordertask.BuyOrder.create(self.storage,
			210000,         #mCent / BTC = 2.1 EUR/BTC
			100000          #mCent       = 1000 EUR
			)

		originalCounterOffer = ordertask.BuyOrder(self.storage, ID, 'buyerAddress')
		self.storage.counterOffers = \
		{40:
			{
			'ID': 40,
			'blob': originalCounterOffer.toPB2().SerializeToString()
			}
		}

		#status -> message:
		expectedMessages = \
		{
		ordertask.TX_STATUS_INITIAL: messages.BL4PStart(
				localOrderID=42,

				amount = 1200,
				sender_timeout_delta_ms = 34,
				locked_timeout_delta_s = 56,
				receiver_pays_fee = True,
				),
		ordertask.TX_STATUS_STARTED: messages.BL4PSelfReport(
				localOrderID=42,

				selfReport = \
					{
					'paymentHash'         : '666f6f', #foo in hex
					'offerID'             : '43',
					'receiverCryptoAmount': '0.00000010000',
					'cryptoCurrency'      : 'btc',
					},
				),
		ordertask.TX_STATUS_LOCKED: messages.LNPay(
				localOrderID=42,

		                destinationNodeID     = 'buyerAddress',
		                offerID               = 43,

		                recipientCryptoAmount = 10000,
		                maxSenderCryptoAmount = 10100,
		                fiatAmount            = 1200,

		                minCLTVExpiryDelta    = 78,

		                paymentHash           = b'foo',
				),
		ordertask.TX_STATUS_RECEIVED_PREIMAGE: messages.BL4PReceive(
				localOrderID=42,

				paymentPreimage = b'bar',
				),
		}

		for status, expectedMessage in expectedMessages.items():
			self.storage.sellTransactions = \
			{
			41:
				{
				'ID': 41,
				'sellOrder': orderID,
				'counterOffer': 40,
				'status': status,

				'buyerFiatAmount': 1200,
				'buyerCryptoAmount': 10000,

				'senderTimeoutDelta': 34,
				'lockedTimeoutDelta': 56,
				'CLTVExpiryDelta'   : 78,

				'paymentHash': b'foo',
				'paymentPreimage': b'bar',
				}
			}

			task = ordertask.OrderTask(self.client, self.storage, order)
			task.startup()

			msg = await self.outgoingMessages.get()
			self.assertEqual(msg, expectedMessage)

			await task.shutdown()

		#Database inconsistency exception:
		self.storage.sellTransactions = \
		{
		41:
			{
			'ID': 41,
			'sellOrder': orderID,
			'counterOffer': 40,
			'status': 100,
			}
		}

		task = ordertask.OrderTask(self.client, self.storage, order)
		with self.assertRaises(Exception):
			await task.continueSellTransaction()


	@asynciotest
	async def test_canceledSellTransaction(self):
		orderID = ordertask.SellOrder.create(self.storage,
			190000,         #mCent / BTC = 1.9 EUR/BTC
			123400000000000 #mSatoshi    = 1234 BTC
			)
		order = ordertask.SellOrder(self.storage, orderID, 'sellerAddress')

		ID = ordertask.BuyOrder.create(self.storage,
			210000,         #mCent / BTC = 2.1 EUR/BTC
			100000          #mCent       = 1000 EUR
			)

		originalCounterOffer = ordertask.BuyOrder(self.storage, ID, 'buyerAddress')
		self.storage.counterOffers = \
		{40:
			{
			'ID': 40,
			'blob': originalCounterOffer.toPB2().SerializeToString()
			}
		}

		#An ongoing tx that is just about to be sent over Lightning:
		self.storage.sellTransactions = \
		{
		41:
			{
			'ID': 41,
			'sellOrder': orderID,
			'counterOffer': 40,
			'status': ordertask.TX_STATUS_LOCKED,

			'buyerFiatAmount': 1200,
			'buyerCryptoAmount': 10000,

			'senderTimeoutDelta': 34,
			'lockedTimeoutDelta': 56,
			'CLTVExpiryDelta'   : 78,

			'paymentHash': b'foo',
			}
		}

		task = ordertask.OrderTask(self.client, self.storage, order)
		task.startup()

		msg = await self.outgoingMessages.get()
		self.assertEqual(msg, messages.LNPay(
				localOrderID=42,

		                destinationNodeID     = 'buyerAddress',
		                offerID               = 43,

		                recipientCryptoAmount = 10000,
		                maxSenderCryptoAmount = 10100,
		                fiatAmount            = 1200,

		                minCLTVExpiryDelta    = 78,

		                paymentHash           = b'foo',
				))

		#Lightning tx ends up canceled:
		task.setCallResult(messages.LNPayResult(
			localOrderID=0,
			paymentHash=b'foo',
			senderCryptoAmount=10500,
			paymentPreimage=None,
			))

		msg = await self.outgoingMessages.get()
		self.assertEqual(msg, messages.BL4PCancelStart(
				localOrderID=42,

				paymentHash = b'foo',
				))

		task.setCallResult(messages.BL4PCancelStartResult(
			request = None,
			))

		msg = await self.outgoingMessages.get()

		self.maxDiff = None
		self.assertEqual(self.storage.sellTransactions, {41:
			{
			'ID': 41,
			'sellOrder': orderID,
			'counterOffer': 40,
			'status': ordertask.TX_STATUS_CANCELED,
			'senderTimeoutDelta': 34,
			'lockedTimeoutDelta': 56,
			'CLTVExpiryDelta':    78,
			'buyerCryptoAmount': 10000,
			'buyerFiatAmount': 1200,
			'paymentHash': b'foo',
			}})
		self.assertEqual(task.transaction, None)

		await task.shutdown()


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
	async def test_doTrading_canceledOrder(self):
		orderID = ordertask.BuyOrder.create(self.storage, 2, 1234)
		order = ordertask.BuyOrder(self.storage, orderID, 'lnAddress')
		task = ordertask.OrderTask(Mock(), None, order)
		order.status = ORDER_STATUS_CANCEL_REQUESTED

		async def dummy():
			pass
		task.continueBuyTransaction = dummy
		task.publishOffer = dummy
		task.waitForIncomingTransaction = dummy
		task.unpublishOffer = dummy
		await task.doTrading()

		self.assertEqual(order.status, ORDER_STATUS_CANCELED)


	@asynciotest
	async def test_doTrading_exceptions(self):
		#Unsupported order type:
		task = ordertask.OrderTask(None, None, None)
		with patch.object(logging, 'exception', Mock()) as logException:
			with self.assertRaises(Exception):
				await task.doTrading()
			logException.assert_called_once()

		#Canceled exception:
		orderID = ordertask.BuyOrder.create(self.storage, 2, 1234)
		order = ordertask.BuyOrder(self.storage, orderID, 'lnAddress')
		task = ordertask.OrderTask(Mock(), None, order)

		async def continueBuyTransaction():
			raise asyncio.CancelledError()

		with patch.object(task, 'continueBuyTransaction', continueBuyTransaction):
			#No exception:
			await task.doTrading()


	@asynciotest
	async def test_doOfferSearch_loop(self):
		order = Mock()
		order.ID = 42
		order.remoteOfferID = None
		task = ordertask.OrderTask(self.client, None, order)

		done = []
		async def doTransaction():
			self.assertEqual(done, [])
			done.append(True)
		task.doTransaction = doTransaction

		searchTask = asyncio.ensure_future(task.doOfferSearch())

		#No BL4P connection:
		received = []
		def raiseNoMessageHandler(msg):
			received.append(msg)
			raise messages.NoMessageHandler()
		with patch.object(self.client, 'handleOutgoingMessage', raiseNoMessageHandler):
			await asyncio.sleep(1)
		self.assertEqual(received, [messages.BL4PFindOffers(
			localOrderID=42,

			query=order,
			)])

		#No results:
		msg = await self.outgoingMessages.get()
		self.assertEqual(msg, messages.BL4PFindOffers(
			localOrderID=42,

			query=order,
			))
		task.setCallResult(messages.BL4PFindOffersResult(
			request = None,
			offers = [],
			))

		#Offer gets published:
		msg = await self.outgoingMessages.get()
		self.assertEqual(msg, messages.BL4PAddOffer(
			localOrderID=42,

			offer=order,
			))
		task.setCallResult(messages.BL4PAddOfferResult(
			request = None,
			ID = 6,
			))

		#No results again:
		t0 = time.time()
		msg = await self.outgoingMessages.get()
		t1 = time.time()
		self.assertAlmostEqual(t1-t0, 1.0, places=2)
		self.assertEqual(msg, messages.BL4PFindOffers(
			localOrderID=42,

			query=order,
			))
		task.setCallResult(messages.BL4PFindOffersResult(
			request = None,
			offers = [],
			))
		self.assertEqual(order.remoteOfferID, 6)

		#Multiple results:
		#Non-matching offers returned by BL4P must not be selected.
		offer0 = Mock()
		offer1 = Mock()
		offer2 = Mock()
		offer0.matches = Mock(return_value = False)
		offer1.matches = Mock(return_value = True)
		offer2.matches = Mock(return_value = True)
		msg = await self.outgoingMessages.get()
		self.assertEqual(msg, messages.BL4PFindOffers(
			localOrderID=42,

			query=order,
			))
		task.setCallResult(messages.BL4PFindOffersResult(
			request = None,
			offers = [offer0, offer1, offer2],
			))

		await searchTask

		self.assertEqual(done, [True])
		self.assertEqual(task.counterOffer, offer1)

		offer0.matches.assert_called_with(order)
		offer1.matches.assert_called_with(order)
		offer2.matches.assert_called_with(order)



if __name__ == '__main__':
	unittest.main(verbosity=2)

