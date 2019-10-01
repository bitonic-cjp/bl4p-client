#    Copyright (C) 2019 by Bitonic B.V.
#
#    This file is part of BL4P Client.
#
#    BL4P Client is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    BL4P Client is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with BL4P Client. If not, see <http://www.gnu.org/licenses/>.

import asyncio
import sys
import unittest
from unittest.mock import Mock, patch

from utils import asynciotest

sys.path.append('..')

from bl4p_api import bl4p_pb2
from bl4p_api import selfreport
from bl4p_api.offer import Offer, Asset
from bl4p_api.serialization import serialize

import messages
import bl4p_interface
Bl4pApi = bl4p_interface.bl4p.Bl4pApi



class TestBL4PInterface(unittest.TestCase):
	def setUp(self):
		self.client = Mock()
		self.interface = bl4p_interface.BL4PInterface(self.client)


	@asynciotest
	async def test_startup(self):
		self.assertEqual(self.interface.client, self.client)
		self.assertEqual(self.interface.handlerMethods,
			{
			messages.BL4PStart      : self.interface.sendStart,
			messages.BL4PSelfReport : self.interface.sendSelfReport,
			messages.BL4PCancelStart: self.interface.sendCancelStart,
			messages.BL4PSend       : self.interface.sendSend,
			messages.BL4PReceive    : self.interface.sendReceive,
			messages.BL4PAddOffer   : self.interface.sendAddOffer,
			messages.BL4PRemoveOffer: self.interface.sendRemoveOffer,
			messages.BL4PFindOffers : self.interface.sendFindOffers,
			})

		startupArgs = []
		async def startup(*args):
			startupArgs.append(args)
		synCallArgs = []
		synCallResult = []
		async def synCall(*args):
			synCallArgs.append(args)
			return synCallResult.pop(0)

		o1 = Mock()
		o1.offerID = 42
		o2 = Mock()
		o2.offerID = 43
		listOffersResult = Mock()
		listOffersResult.offers = [o1, o2]
		synCallResult.append(listOffersResult) #ListOffers return value
		synCallResult.append(None) #RemoveOffer return value
		synCallResult.append(None) #RemoveOffer return value

		with patch.object(Bl4pApi, 'startup', startup):
			with patch.object(self.interface, 'synCall', synCall):
				await self.interface.startup('foo', 'bar', 'baz')

		self.assertEqual(startupArgs, [(self.interface, 'foo', 'bar', 'baz')])

		self.assertEqual(len(synCallArgs), 3)
		for args in synCallArgs:
			self.assertEqual(len(args), 1)
		self.assertTrue(isinstance(synCallArgs[0][0], bl4p_pb2.BL4P_ListOffers))
		self.assertTrue(isinstance(synCallArgs[1][0], bl4p_pb2.BL4P_RemoveOffer))
		self.assertTrue(isinstance(synCallArgs[2][0], bl4p_pb2.BL4P_RemoveOffer))
		self.assertEqual(synCallArgs[1][0].offerID, 42)
		self.assertEqual(synCallArgs[2][0].offerID, 43)


	def doSingleSendTest(self, msgIn, expectedMsgOut):
		self.interface.sendQueue = Mock()
		self.interface.lastRequestID = 6
		self.interface.handleMessage(msgIn)
		self.assertEqual(self.interface.lastRequestID, 7)
		expectedMsgOut.request = 6
		self.interface.sendQueue.put_nowait.assert_called_with(
			serialize(expectedMsgOut)
			)
		self.assertEqual(self.interface.activeRequests[6], msgIn)


	def test_sendStart(self):
		msgIn = messages.BL4PStart(
			localOrderID = 0,
			amount = 1234,
			sender_timeout_delta_ms = 100,
			locked_timeout_delta_s = 1000000,
			receiver_pays_fee = False,
			)
		expectedMsgOut = bl4p_pb2.BL4P_Start()
		expectedMsgOut.amount.amount = 1234
		expectedMsgOut.sender_timeout_delta_ms = 100
		expectedMsgOut.locked_timeout_delta_s = 1000000
		expectedMsgOut.receiver_pays_fee = False
		self.doSingleSendTest(msgIn, expectedMsgOut)


	def test_sendSelfReport(self):
		msgIn = messages.BL4PSelfReport(
			localOrderID = 0,
			selfReport = {'foo': 'bar'},
			)
		expectedMsgOut = bl4p_pb2.BL4P_SelfReport()
		expectedMsgOut.report = selfreport.serialize({'foo': 'bar'})
		expectedMsgOut.signature = b'Dummy Signature' #TODO
		self.doSingleSendTest(msgIn, expectedMsgOut)


	def test_sendCancelStart(self):
		msgIn = messages.BL4PCancelStart(
			localOrderID = 0,
			paymentHash = b'foobar',
			)
		expectedMsgOut = bl4p_pb2.BL4P_CancelStart()
		expectedMsgOut.payment_hash.data = b'foobar'
		self.doSingleSendTest(msgIn, expectedMsgOut)


	def test_sendSend(self):
		msgIn = messages.BL4PSend(
			localOrderID = 0,
			amount = 1234,
			paymentHash = b'foobar',
			max_locked_timeout_delta_s = 5000,
			selfReport = {'foo': 'bar'},
			)
		expectedMsgOut = bl4p_pb2.BL4P_Send()
		expectedMsgOut.sender_amount.amount = 1234
		expectedMsgOut.payment_hash.data = b'foobar'
		expectedMsgOut.max_locked_timeout_delta_s = 5000
		expectedMsgOut.report = selfreport.serialize({'foo': 'bar'})
		expectedMsgOut.signature = b'Dummy Signature' #TODO
		self.doSingleSendTest(msgIn, expectedMsgOut)


	def test_sendReceive(self):
		msgIn = messages.BL4PReceive(
			localOrderID = 0,
			paymentPreimage = b'foobar',
			)
		expectedMsgOut = bl4p_pb2.BL4P_Receive()
		expectedMsgOut.payment_preimage.data = b'foobar'
		self.doSingleSendTest(msgIn, expectedMsgOut)


	def test_sendAddOffer(self):
		offer = Offer(
			bid = Asset(1234, 100, 'eur', 'bl3p.eu'),
			ask = Asset(4321, 100000, 'btc', 'ln'),
			address = 'bar',
			ID = 42,
			)
		msgIn = messages.BL4PAddOffer(
			localOrderID = 0,
			offer = offer,
			)
		expectedMsgOut = bl4p_pb2.BL4P_AddOffer()
		expectedMsgOut.offer.CopyFrom(offer.toPB2())
		self.doSingleSendTest(msgIn, expectedMsgOut)


	def test_sendRemoveOffer(self):
		msgIn = messages.BL4PRemoveOffer(
			localOrderID = 0,
			offerID = 42,
			)
		expectedMsgOut = bl4p_pb2.BL4P_RemoveOffer()
		expectedMsgOut.offerID = 42
		self.doSingleSendTest(msgIn, expectedMsgOut)


	def test_sendFindOffers(self):
		query = Offer(
			bid = Asset(1234, 100, 'eur', 'bl3p.eu'),
			ask = Asset(4321, 100000, 'btc', 'ln'),
			address = 'bar',
			ID = 42,
			)
		msgIn = messages.BL4PFindOffers(
			localOrderID = 0,
			query = query,
			)
		expectedMsgOut = bl4p_pb2.BL4P_FindOffers()
		expectedMsgOut.query.CopyFrom(query.toPB2())
		self.doSingleSendTest(msgIn, expectedMsgOut)


	def test_handleResult_regularMessages(self):
		def testSingleMessage(msg):
			self.interface.activeRequests = {6: 'baz'}
			msg.request = 6

			result = []
			def handleIncomingMessage(message):
				result.append(message)

			with patch.object(self.interface.client, 'handleIncomingMessage', handleIncomingMessage):
				self.interface.handleResult(msg)

			self.assertEqual(self.interface.activeRequests, {})
			self.assertEqual(len(result), 1)
			self.assertEqual(result[0].request, 'baz')
			return result[0]

		msg = bl4p_pb2.BL4P_StartResult()
		msg.sender_amount.amount = 1234
		msg.receiver_amount.amount = 1230
		msg.payment_hash.data = b'foobar'
		msg = testSingleMessage(msg)
		self.assertTrue(isinstance(msg, messages.BL4PStartResult))
		self.assertEqual(msg.senderAmount, 1234)
		self.assertEqual(msg.receiverAmount, 1230)
		self.assertEqual(msg.paymentHash, b'foobar')

		msg = bl4p_pb2.BL4P_SelfReportResult()
		msg = testSingleMessage(msg)
		self.assertTrue(isinstance(msg, messages.BL4PSelfReportResult))

		msg = bl4p_pb2.BL4P_CancelStartResult()
		msg = testSingleMessage(msg)
		self.assertTrue(isinstance(msg, messages.BL4PCancelStartResult))

		msg = bl4p_pb2.BL4P_SendResult()
		msg.payment_preimage.data = b'foobar'
		msg = testSingleMessage(msg)
		self.assertTrue(isinstance(msg, messages.BL4PSendResult))
		self.assertEqual(msg.paymentPreimage, b'foobar')

		msg = bl4p_pb2.BL4P_ReceiveResult()
		msg = testSingleMessage(msg)
		self.assertTrue(isinstance(msg, messages.BL4PReceiveResult))

		msg = bl4p_pb2.BL4P_AddOfferResult()
		msg.offerID = 42
		msg = testSingleMessage(msg)
		self.assertTrue(isinstance(msg, messages.BL4PAddOfferResult))
		self.assertEqual(msg.ID, 42)

		msg = bl4p_pb2.BL4P_RemoveOfferResult()
		msg = testSingleMessage(msg)
		self.assertTrue(isinstance(msg, messages.BL4PRemoveOfferResult))

		msg = bl4p_pb2.BL4P_FindOffersResult()
		o1 = Offer(
			bid = Asset(1234, 100, 'eur', 'bl3p.eu'),
			ask = Asset(4321, 100000, 'btc', 'ln'),
			address = 'bar',
			ID = 42,
			)
		msg.offers.add().CopyFrom(o1.toPB2())
		o2 = Offer(
			ask = Asset(1234, 100, 'eur', 'bl3p.eu'),
			bid = Asset(4321, 100000, 'btc', 'ln'),
			address = 'baz',
			ID = 43,
			)
		msg.offers.add().CopyFrom(o2.toPB2())
		msg = testSingleMessage(msg)
		self.assertTrue(isinstance(msg, messages.BL4PFindOffersResult))
		self.assertEqual(len(msg.offers), 2)
		self.assertEqual(msg.offers[0], o1)
		self.assertEqual(msg.offers[1], o2)

		msg = bl4p_pb2.Error()
		msg = testSingleMessage(msg)
		self.assertTrue(isinstance(msg, messages.BL4PError))


	def test_handleResult_unrecognized(self):
		#Just testing coverage without exceptions
		self.interface.activeRequests = {6: 'baz'}
		msg = bl4p_pb2.BL4P_CancelStart()
		msg.request = 6
		self.interface.handleResult(msg)

		#TODO: handle the case of types without request attribute
		#TODO: handle the case of invalid request number



if __name__ == '__main__':
	unittest.main(verbosity=2)

