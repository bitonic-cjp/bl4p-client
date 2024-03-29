#    Copyright (C) 2019-2021 by Bitonic B.V.
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
import logging
import sys
import unittest
from unittest.mock import Mock, patch

from utils import asynciotest, DummyReader, DummyWriter

sys.path.append('..')

import messages
import plugin_interface



class TestPluginInterface(unittest.TestCase):
	def setUp(self):
		self.client = Mock()
		self.input = DummyReader()
		self.output = DummyWriter()
		self.interface = plugin_interface.PluginInterface(self.client, self.input, self.output)


	def checkJSON(self, data, *args):
		obj, length = json.JSONDecoder().raw_decode(data.decode('UTF-8'))
		#If any is a match, accept
		for reference in args:
			if obj == reference:
				return
		#Otherwise, let this assertion fail
		self.assertEqual(obj, args[0])


	def checkJSONOutput(self, *args):
		self.checkJSON(self.output.buffer, *args)
		self.output.buffer = b''


	@asynciotest
	async def test_startup(self):
		self.assertEqual(self.interface.inputStream, self.input)
		self.assertEqual(self.interface.outputStream, self.output)
		self.assertEqual(self.interface.client, self.client)
		self.assertEqual(self.interface.handlerMethods,
			{
			messages.LNFinish: self.interface.sendFinish,
			messages.LNFail: self.interface.sendFail,
			messages.PluginCommandResult: self.interface.sendPluginCommandResult,
			messages.PluginCommandError: self.interface.sendPluginCommandError,
			})

		called = []
		async def setCalled():
			called.append(True)

		self.interface.handleIncomingData = setCalled
		self.input.buffer =  b'{"id": 0, "method": "getmanifest", "params": {}}\n\n'
		self.input.buffer += b'{"id": 1, "method": "init", "params": {"options": {"bl4p.logfile": "foo", "bl4p.dbfile": "bar"}, "configuration": {"lightning-dir": "foobar", "rpc-file": "baz"}}}\n\n'
		await self.interface.startup()
		await asyncio.sleep(0.1)
		await self.interface.shutdown()

		output = self.output.buffer.split(b'\n\n')
		self.assertEqual(len(output), 3)

		#getmanifest output
		obj, length = json.JSONDecoder().raw_decode(output[0].decode('UTF-8'))
		self.assertEqual(obj['id'], 0)
		obj = obj['result']
		self.assertEqual(obj['subscriptions'], [])
		self.assertEqual(obj['options'][0]['name'], 'bl4p.logfile')
		self.assertEqual(obj['options'][0]['default'], 'bl4p.log')
		self.assertEqual(obj['options'][1]['name'], 'bl4p.dbfile')
		self.assertEqual(obj['options'][1]['default'], 'bl4p.db')
		self.assertEqual(obj['hooks'], ['htlc_accepted'])
		names = [m['name'] for m in obj['rpcmethods']]
		self.assertEqual(set(names),
			set(['bl4p.getfiatcurrency', 'bl4p.getcryptocurrency', 'bl4p.buy', 'bl4p.sell', 'bl4p.list', 'bl4p.cancel', 'bl4p.setconfig', 'bl4p.getconfig']))

		#init output
		self.checkJSON(output[1],
			{
			'jsonrpc': '2.0',
			'id': 1,
			'result': None,
			})
		self.assertEqual(output[2], b'')

		self.assertEqual(self.interface.RPCPath, 'foobar/baz')
		self.assertEqual(self.interface.logFile, 'foo')
		self.assertEqual(self.interface.DBFile, 'bar')


	@asynciotest
	async def test_startup_earlyClose(self):
		#In case no init message arrives before close, raise an exception
		with self.assertRaises(Exception):
			await self.interface.startup()


	def test_ongoingRequests(self):
		self.interface.currentRequestID = 6
		self.interface.storeOngoingRequest('foo', 'bar')
		self.interface.currentRequestID = 7
		self.interface.storeOngoingRequest('foo', 'baz')

		self.assertEqual(
			self.interface.findOngoingRequest('foo', lambda s: s=='bar'),
			6)
		self.assertEqual(
			self.interface.findOngoingRequest('foo', lambda s: s=='baz'),
			7)
		with self.assertRaises(IndexError):
			self.interface.findOngoingRequest('foo', lambda s: s=='baa')

		self.interface.sendOngoingRequestResponse(6, 'response')

		with self.assertRaises(IndexError):
			self.interface.findOngoingRequest('foo', lambda s: s=='bar')


	def test_GetFiatCurrency(self):
		self.interface.handleRequest(0, 'bl4p.getfiatcurrency', {})
		self.checkJSONOutput(
			{
			'jsonrpc': '2.0',
			'id': 0,
			'result': {'divisor': 100000, 'name': 'eur'},
			})


	def test_GetCryptoCurrency(self):
		self.interface.handleRequest(0, 'bl4p.getcryptocurrency', {})
		self.checkJSONOutput(
			{
			'jsonrpc': '2.0',
			'id': 0,
			'result': {'divisor': 100000000000, 'name': 'btc'},
			})


	def test_Buy(self):
		self.interface.handleRequest(2, 'bl4p.buy', {'limit_rate': 42, 'amount': 6})
		self.assertEqual(self.output.buffer, b'')
		self.client.handleIncomingMessage.assert_called_once_with(messages.BuyCommand(
			commandID=2,
			limitRate=42,
			amount=6,
			))
		self.interface.handleMessage(messages.PluginCommandResult(
			commandID=2,
			result=None,
			))
		self.checkJSONOutput(
			{
			'jsonrpc': '2.0',
			'id': 2,
			'result': None,
			})


	def test_Buy_error(self):
		self.interface.handleRequest(2, 'bl4p.buy', {'limit_rate': 42, 'amount': 6})
		self.assertEqual(self.output.buffer, b'')
		self.client.handleIncomingMessage.assert_called_once_with(messages.BuyCommand(
			commandID=2,
			limitRate=42,
			amount=6,
			))
		self.interface.handleMessage(messages.PluginCommandError(
			commandID=2,
			code=11,
			message='fubar',
			))
		self.checkJSONOutput(
			{
			'jsonrpc': '2.0',
			'id': 2,
			'error': {'code': 11, 'message': 'fubar'},
			})


	def test_Sell(self):
		self.interface.handleRequest(2, 'bl4p.sell', {'limit_rate': 42, 'amount': 6})
		self.assertEqual(self.output.buffer, b'')
		self.client.handleIncomingMessage.assert_called_once_with(messages.SellCommand(
			commandID=2,
			limitRate=42,
			amount=6,
			))
		self.interface.handleMessage(messages.PluginCommandResult(
			commandID=2,
			result=None,
			))
		self.checkJSONOutput(
			{
			'jsonrpc': '2.0',
			'id': 2,
			'result': None,
			})


	def test_List(self):
		self.interface.handleRequest(6, 'bl4p.list', {})
		self.assertEqual(self.output.buffer, b'')
		self.client.handleIncomingMessage.assert_called_once_with(messages.ListCommand(
			commandID=6,
			))

		self.interface.handleMessage(messages.PluginCommandResult(
			commandID=6,
			result={'sell':[], 'buy':[]},
			))
		self.checkJSONOutput(
			{
			'jsonrpc': '2.0',
			'id': 6,
			'result': {'sell':[], 'buy':[]},
			})


	def test_Cancel(self):
		self.interface.handleRequest(6, 'bl4p.cancel', {'orderID': 42})
		self.assertEqual(self.output.buffer, b'')
		self.client.handleIncomingMessage.assert_called_once_with(messages.CancelCommand(
			commandID=6,
			orderID=42,
			))

		self.interface.handleMessage(messages.PluginCommandResult(
			commandID=6,
			result=None,
			))
		self.checkJSONOutput(
			{
			'jsonrpc': '2.0',
			'id': 6,
			'result': None,
			})


	def test_setConfig(self):
		self.interface.handleRequest(6, 'bl4p.setconfig', {'values': {'foo': 'xx', 'bar': 'yy'}})
		self.assertEqual(self.output.buffer, b'')
		self.client.handleIncomingMessage.assert_called_once_with(messages.SetConfigCommand(
			commandID=6,
			values={'foo': 'xx', 'bar': 'yy'},
			))
		self.interface.handleMessage(messages.PluginCommandResult(
			commandID=2,
			result=None,
			))
		self.checkJSONOutput(
			{
			'jsonrpc': '2.0',
			'id': 2,
			'result': None,
			})


	def test_getConfig(self):
		self.interface.handleRequest(6, 'bl4p.getconfig', {})
		self.assertEqual(self.output.buffer, b'')
		self.client.handleIncomingMessage.assert_called_once_with(messages.GetConfigCommand(
			commandID=6,
			))
		self.interface.handleMessage(messages.PluginCommandResult(
			commandID=2,
			result={'values': {'a': 'foo', 'b': 'bar'}},
			))
		self.checkJSONOutput(
			{
			'jsonrpc': '2.0',
			'id': 2,
			'result': {'values': {'a': 'foo', 'b': 'bar'}},
			})


	def test_handleHTLCAccepted_goodFlow(self):
		self.interface.handleRequest(
			6,
			'htlc_accepted',
			{
			'onion':
				{
				'payload': '12fe424c34500cf1f2f3f4f5f6f7f8c1c2c3c4',
				},
			'htlc':
				{
				'amount': '1234msat',
				'cltv_expiry': 42,
				'payment_hash': 'cafecafe',
				},
			})
		self.assertEqual(self.output.buffer, b'')
		self.client.handleIncomingMessage.assert_called_once_with(messages.LNIncoming(
			paymentHash = b'\xca\xfe\xca\xfe',
			cryptoAmount = 1234,
			CLTVExpiryDelta = 42,
			fiatAmount = 0xf1f2f3f4f5f6f7f8,
			offerID = 0xc1c2c3c4,
			))

		self.interface.handleMessage(messages.LNFinish(
			paymentHash = b'\xca\xfe\xca\xfe',
			paymentPreimage = b'\xb0\x0b\x13',
			))
		self.checkJSONOutput(
			{
			'jsonrpc': '2.0',
			'id': 6,
			'result':
				{
				'result': 'resolve',
				'payment_key': 'b00b13',
				},
			})


	def test_handleHTLCAccepted_failed(self):
		self.interface.handleRequest(
			6,
			'htlc_accepted',
			{
			'onion':
				{
				'payload': '12fe424c34500cf1f2f3f4f5f6f7f8c1c2c3c4',
				},
			'htlc':
				{
				'amount': '1234msat',
				'cltv_expiry': 42,
				'payment_hash': 'cafecafe',
				},
			})
		self.assertEqual(self.output.buffer, b'')
		self.client.handleIncomingMessage.assert_called_once_with(messages.LNIncoming(
			paymentHash = b'\xca\xfe\xca\xfe',
			cryptoAmount = 1234,
			CLTVExpiryDelta = 42,
			fiatAmount = 0xf1f2f3f4f5f6f7f8,
			offerID = 0xc1c2c3c4,
			))

		self.interface.handleMessage(messages.LNFail(
			paymentHash = b'\xca\xfe\xca\xfe',
			))
		self.checkJSONOutput(
			{
			'jsonrpc': '2.0',
			'id': 6,
			'result':
				{
				'result': 'fail',
				},
			})


	def test_handleHTLCAccepted_notOurPayload(self):
		m = Mock(return_value=None)
		with patch.object(logging, 'exception', m):
			self.interface.handleRequest(
				6,
				'htlc_accepted',
				{
				'onion':
					{
					'payload': '12fe4c4c34500cf1f2f3f4f5f6f7f8c1c2c3c4',
					},
				'htlc':
					{
					'amount': '1234msat',
					'cltv_expiry': 42,
					'payment_hash': 'cafecafe',
					},
				})
		m.assert_called_once()
		self.checkJSONOutput(
			{
			'jsonrpc': '2.0',
			'id': 6,
			'result':
				{
				'result': 'continue',
				},
			})


	def test_handleHTLCAccepted_wrongFormatPayload(self):
		m = Mock(return_value=None)
		with patch.object(logging, 'exception', m):
			self.interface.handleRequest(
				6,
				'htlc_accepted',
				{
				'onion':
					{
					'payload': '11fe424c34500bf1f2f3f4f5f6f7f8c1c2c3',
					},
				'htlc':
					{
					'amount': '1234msat',
					'cltv_expiry': 42,
					'payment_hash': 'cafecafe',
					},
				})
		m.assert_called_once()
		self.checkJSONOutput(
			{
			'jsonrpc': '2.0',
			'id': 6,
			'result':
				{
				'result': 'fail',
				},
			})


	def test_sendFinish_withoutCall(self):
		#This must be a NOP:
		self.interface.handleMessage(messages.LNFinish(
			paymentHash = b'\xca\xfe\xca\xfe',
			paymentPreimage = b'\xb0\x0b\x13',
			))
		self.assertEqual(self.output.buffer, b'')


	def test_sendFail_withoutCall(self):
		#This must be a NOP:
		self.interface.handleMessage(messages.LNFail(
			paymentHash = b'\xca\xfe\xca\xfe',
			))
		self.assertEqual(self.output.buffer, b'')


	def test_invalidRequest(self):
		m = Mock(return_value=None)
		with patch.object(logging, 'exception', m):
			self.interface.handleRequest(6, 'does_not_exist', {})
		m.assert_called_once()
		self.checkJSONOutput(
			{
			'jsonrpc': '2.0',
			'id': 6,
			'error':
				{
				'code': 1,
				'message': "Error while processing does_not_exist: KeyError('does_not_exist',)", #with comma
				},
			},
			{
			'jsonrpc': '2.0',
			'id': 6,
			'error':
				{
				'code': 1,
				'message': "Error while processing does_not_exist: KeyError('does_not_exist')", #without comma
				},
			})


	def test_getManifest(self):
		#Mostly to get 100% coverage
		def f1():
			'Function with docstring'
			pass
		def f2():
			#Function without docstring
			pass
		self.interface.methods = \
		{
		'with'   : (f1, plugin_interface.MethodType.RPCMETHOD),
		'without': (f2, plugin_interface.MethodType.RPCMETHOD),
		}
		result = self.interface.getManifest()
		result = set([(x['name'], x['description']) for x in result['rpcmethods']])
		self.assertEqual(result,
			set([
			('with', 'Function with docstring'),
			('without', 'Undocumented RPC method from a plugin.'),
			])
			)



if __name__ == '__main__':
	unittest.main(verbosity=2)

