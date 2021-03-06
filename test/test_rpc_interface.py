#    Copyright (C) 2019-2020 by Bitonic B.V.
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
import json
import sys
import unittest
from unittest.mock import Mock

from utils import asynciotest, DummyReader, DummyWriter

sys.path.append('..')

import messages
import rpc_interface



class TestRPCInterface(unittest.TestCase):
	def setUp(self):
		self.client = Mock()
		self.input = DummyReader()
		self.output = DummyWriter()
		self.rpc = rpc_interface.RPCInterface(self.client, self.input, self.output)


	@asynciotest
	async def test_startupRPC(self):
		self.assertEqual(self.rpc.inputStream, self.input)
		self.assertEqual(self.rpc.outputStream, self.output)
		self.assertEqual(self.rpc.client, self.client)
		self.assertEqual(self.rpc.handlerMethods, {messages.LNPay: self.rpc.sendPay})

		called = []
		async def setCalled():
			called.append(True)

		self.rpc.handleIncomingData = setCalled
		self.input.buffer = b'{"id": 0, "result": {"id": "foo"}}\n\n'
		await self.rpc.startupRPC()
		await asyncio.sleep(0.1)
		await self.rpc.shutdown()

		self.assertEqual(called, [True])
		self.assertEqual(self.input.buffer, b'')
		self.assertEqual(self.rpc.nodeID, 'foo')


	def checkJSONOutput(self, reference):
		obj, length = json.JSONDecoder().raw_decode(self.output.buffer.decode('UTF-8'))
		self.assertEqual(obj, reference)
		self.output.buffer = b''


	def test_sendPay_goodFlow(self):
		msg = messages.LNPay(
			localOrderID = 6,
			destinationNodeID = 'Destination',
			maxSenderCryptoAmount = 1248,
			recipientCryptoAmount = 1234,
			minCLTVExpiryDelta = 42,
			fiatAmount = 0xdeadbeef,
			offerID = 0x8008,
			paymentHash = bytes.fromhex('0123456789abcdef'),
			)

		self.rpc.handleMessage(msg)

		self.checkJSONOutput(
			{
			'jsonrpc': '2.0',
			'id': 0,
			'method': 'getroute',
			'params': {'cltv': 42, 'id': 'Destination', 'msatoshi': 1234, 'riskfactor': 1},
			})

		self.rpc.handleResult(0,
			{
			'route':
				[
				{
				'id': 'Intermediate',
				'msatoshi': 1247,
				'delay': 12,
				'channel': '103x1x1',
				'style': 'legacy'
				},
				{
				'id': 'Destination',
				'msatoshi': 1234,
				'delay': 10,
				'channel': '199x2x3',
				'style': 'legacy'
				},
				],
			})

		self.checkJSONOutput(
			{
			'jsonrpc': '2.0',
			'id': 1,
			'method': 'getinfo',
			'params':
				{
				},
			})

		self.rpc.handleResult(1,
			{
			'blockheight': 123456,
			})

		self.checkJSONOutput(
			{
			'jsonrpc': '2.0',
			'id': 2,
			'method': 'createonion',
			'params':
				{
				'hops':
					[
					{'payload': '000000c7000002000300000000000004d20001e24a000000000000000000000000000000000000000000000000', 'pubkey': 'Intermediate'},
					{'payload': '12fe424c34500c00000000deadbeef00008008', 'pubkey': 'Destination'}
					],
				'assocdata': '0123456789abcdef',
				}
			})

		self.rpc.handleResult(2,
			{
			'onion': 'The onion',
			'shared_secrets': ['Secret 1', 'Secret 2'],
			})

		self.checkJSONOutput(
			{
			'jsonrpc': '2.0',
			'id': 3,
			'method': 'sendonion',
			'params':
				{
				'onion': 'The onion',
				'first_hop':
					{
					'id': 'Intermediate',
					'msatoshi': 1247,
					'delay': 12,
					'channel': '103x1x1',
					'style': 'legacy'
					},
				'payment_hash': '0123456789abcdef',
				'label': 'BL4P payment',
				'shared_secrets': ['Secret 1', 'Secret 2'],
				'msatoshi': 1234,
				},
			})

		self.rpc.handleResult(3, {})

		self.checkJSONOutput(
			{
			'jsonrpc': '2.0',
			'id': 4,
			'method': 'waitsendpay',
			'params':
				{
				'payment_hash': '0123456789abcdef',
				},
			})

		self.rpc.handleResult(4,
			{
			'status': 'complete',
			'payment_preimage': 'cafecafe',
			})

		self.client.handleIncomingMessage.assert_called_once_with(messages.LNPayResult(
			localOrderID = 6,
			senderCryptoAmount = 1247,
			paymentHash = bytes.fromhex('0123456789abcdef'),
			paymentPreimage = bytes.fromhex('cafecafe'),
			))


	def test_sendPay_maxSenderCryptoAmountExceeded(self):
		msg = messages.LNPay(
			localOrderID = 6,
			destinationNodeID = 'Destination',
			maxSenderCryptoAmount = 1248,
			recipientCryptoAmount = 1234,
			minCLTVExpiryDelta = 42,
			fiatAmount = 0xdeadbeef,
			offerID = 0x8008,
			paymentHash = bytes.fromhex('0123456789abcdef'),
			)

		self.rpc.handleMessage(msg)

		self.checkJSONOutput(
			{
			'jsonrpc': '2.0',
			'id': 0,
			'method': 'getroute',
			'params': {'cltv': 42, 'id': 'Destination', 'msatoshi': 1234, 'riskfactor': 1},
			})

		with self.assertRaises(Exception):
			self.rpc.handleResult(0,
				{
				'route': [{'msatoshi': 1249}, {'msatoshi': 1234}],
				})


	def test_sendPay_recipientRefusedTransaction(self):
		msg = messages.LNPay(
			localOrderID = 6,
			destinationNodeID = 'Destination',
			maxSenderCryptoAmount = 1248,
			recipientCryptoAmount = 1234,
			minCLTVExpiryDelta = 42,
			fiatAmount = 0xdeadbeef,
			offerID = 0x8008,
			paymentHash = bytes.fromhex('0123456789abcdef'),
			)
		self.rpc.handleMessage(msg)
		self.rpc.handleResult(0,
			{
			'route':
				[
				{
				'id': 'Intermediate',
				'msatoshi': 1247,
				'delay': 12,
				'channel': '103x1x1',
				'style': 'legacy'
				},
				{
				'id': 'Destination',
				'msatoshi': 1234,
				'delay': 10,
				'channel': '199x2x3',
				'style': 'legacy'
				},
				],
			})

		self.rpc.handleResult(1,
			{
			'blockheight': 123456,
			})

		self.rpc.handleResult(2,
			{
			'onion': 'The onion',
			'shared_secrets': ['Secret 1', 'Secret 2'],
			})

		self.output.buffer = b''

		self.rpc.handleResult(3, {})

		self.checkJSONOutput(
			{
			'jsonrpc': '2.0',
			'id': 4,
			'method': 'waitsendpay',
			'params':
				{
				'payment_hash': '0123456789abcdef',
				},
			})

		self.rpc.handleError(4, 203, 'Transaction was refused')

		self.client.handleIncomingMessage.assert_called_once_with(messages.LNPayResult(
			localOrderID = 6,
			senderCryptoAmount = 1247,
			paymentHash = bytes.fromhex('0123456789abcdef'),
			paymentPreimage = None,
			))


	def test_storedRequestResult_bug(self):
		#This can only happen if there's a bug in the code.
		with self.assertRaises(Exception):
			self.rpc.handleStoredRequestResult(object(), 'foo', {})


	def test_storedRequestError_unhandled(self):
		#TODO: maybe this should raise an exception?
		self.rpc.handleStoredRequestError(object(), 'foo', None)



if __name__ == '__main__':
	unittest.main(verbosity=2)

