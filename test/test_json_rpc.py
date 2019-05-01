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
import json
import sys
import unittest
from unittest.mock import Mock, patch

from utils import asynciotest

sys.path.append('..')

import json_rpc



class DummyWriter:
	def __init__(self):
		self.buffer = b''


	def write(self, data):
		self.buffer += data


class DummyReader:
	def __init__(self):
		self.buffer = b''


	async def read(self, n):
		ret = self.buffer[:n]
		self.buffer = self.buffer[n:]
		return ret



class TestJSONRPC(unittest.TestCase):
	def setUp(self):
		self.input = DummyReader()
		self.output = DummyWriter()
		self.rpc = json_rpc.JSONRPC(self.input, self.output)


	@asynciotest
	async def test_task(self):
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

		self.rpc.handleIncomingData = count
		self.rpc.startup()
		await asyncio.sleep(0.35)
		await self.rpc.shutdown()
		self.assertEqual(result, [1, 2, 3])

		result = []

		async def countTo3():
			for i in range(1, 4):
				await asyncio.sleep(0.1)
				result.append(i)

		self.rpc.handleIncomingData = countTo3
		self.rpc.startup()
		await self.rpc.waitFinished()
		self.assertEqual(result, [1, 2, 3])


	@asynciotest
	async def test_incomingDataExceptions(self):
		for eType in [asyncio.CancelledError, BrokenPipeError, Exception]:
			async def read(n):
				raise eType('Intended test exception')

			self.input.read = read

			m = Mock(return_value=None)
			with patch.object(json_rpc, 'logException', m):
				await self.rpc.handleIncomingData()

			if eType == Exception: #only in this case
				m.assert_called_once_with()


	@asynciotest
	async def test_incomingDataEOF(self):
		#It must finish without exceptions
		await self.rpc.handleIncomingData()


	@asynciotest
	async def test_incomingJSON(self):
		self.input.buffer = b'{"method": "foo", "params": {"bar": 0, "baz": null}}'
		m = Mock(return_value=None)
		with patch.object(self.rpc, 'handleNotification', m):
			await self.rpc.handleIncomingData()
			m.assert_called_once_with('foo', {'bar': 0, 'baz': None})

		self.input.buffer = b'{"id": 3, "method": "foo", "params": {"bar": 0, "baz": null}}'
		m = Mock(return_value=None)
		with patch.object(self.rpc, 'handleRequest', m):
			await self.rpc.handleIncomingData()
			m.assert_called_once_with(3, 'foo', {'bar': 0, 'baz': None})

		self.input.buffer = b'{"id": 3, "result": {"bar": 0, "baz": null}}'
		m = Mock(return_value=None)
		with patch.object(self.rpc, 'handleResult', m):
			await self.rpc.handleIncomingData()
			m.assert_called_once_with(3, {'bar': 0, 'baz': None})

		self.input.buffer = b'{"id": 3, "error": "bar"}'
		m = Mock(return_value=None)
		with patch.object(self.rpc, 'handleError', m):
			await self.rpc.handleIncomingData()
			m.assert_called_once_with(3, 'bar')

		self.input.buffer = b'{"info": "Dummy JSON data"}'
		m = Mock(return_value=None)
		with patch.object(json_rpc, 'logException', m):
			await self.rpc.handleIncomingData()
			m.assert_called_once_with()

		self.input.buffer = b'{' * (1024*1024+1)
		m = Mock(return_value=None)
		with patch.object(json_rpc, 'logException', m):
			await self.rpc.handleIncomingData()
			m.assert_called_once_with()


	@asynciotest
	async def test_defaultHandlerMethods(self):
		#No assertions, just do code coverage and check there are no exceptions
		self.input.buffer = b'{"method": "foo", "params": {}}{"id": 3, "method": "foo", "params": {}}{"id": 3, "result": {}}{"id": 3, "error": "bar"}'
		await self.rpc.handleIncomingData()


	def test_outgoingJSON(self):
		def testJSONWritten(obj):
			self.assertTrue(self.output.buffer.startswith(b'{'))
			self.assertTrue(self.output.buffer.endswith(b'}\n\n'))
			obj2, length = json.JSONDecoder().raw_decode(self.output.buffer.decode('UTF-8'))
			self.assertEqual(obj2, obj)
			self.assertEqual(length, len(self.output.buffer) - 2)
			self.output.buffer = b''

		self.assertEqual(self.rpc.outgoingRequestID, 0)
		self.rpc.outgoingRequestID = 42
		ID = self.rpc.sendRequest('foo', {'bar': 0, 'baz': None})
		testJSONWritten({'jsonrpc': '2.0', 'id': 42, 'method': 'foo', 'params': {'baz': None, 'bar': 0}})
		self.assertEqual(ID, 42)
		self.assertEqual(self.rpc.outgoingRequestID, 43)

		self.rpc.sendResponse(6, {'bar': 0, 'baz': None})
		testJSONWritten({'jsonrpc': '2.0', 'id': 6, 'result': {'baz': None, 'bar': 0}})

		self.rpc.sendErrorResponse(6, 'bar')
		testJSONWritten({'jsonrpc': '2.0', 'id': 6, 'error': 'bar'})

		self.rpc.sendNotification('foo', {'bar': 0, 'baz': None})
		testJSONWritten({'jsonrpc': '2.0', 'method': 'foo', 'params': {'baz': None, 'bar': 0}})


	@asynciotest
	async def test_synCall(self):
		self.input.buffer = b'{"id": 41, "result": {}}\n\n{"id": 42, "result": "bar"}\n\n'
		self.rpc.outgoingRequestID = 42
		result = await self.rpc.synCall('foo', {'baz': 0})
		self.assertEqual(result, 'bar')

		self.input.buffer = b'{"id": 43, "error": "bar"}\n\n'
		with self.assertRaises(Exception) as r:
			await self.rpc.synCall('foo', {'baz': 0})
		self.assertEqual(str(r.exception), 'bar')



if __name__ == '__main__':
	unittest.main(verbosity=2)

