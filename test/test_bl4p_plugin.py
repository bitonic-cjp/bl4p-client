#    Copyright (C) 2019-2020 by Bitonic B.V.
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
import json
import subprocess
import sys
import unittest
from unittest.mock import Mock, patch

import secp256k1

from utils import asynciotest, DummyReader, DummyWriter

sys.path.append('..')

import bl4p_interface
import bl4p_plugin



class MockConfiguration:
	def __init__(self):
		self.values = {}

	def setValue(self, name, value):
		self.values[name] = value

	def getValue(self, name):
		return self.values[name]



class TestPlugin(unittest.TestCase):
	def test_stdio(self):
		proc = subprocess.run(
			['python3', 'test_bl4p_plugin.py', 'stdio'],
			input=b'foo',
			stdout=subprocess.PIPE, stderr=subprocess.PIPE,
			env={'COVERAGE_PROCESS_START': '.coveragerc'},
			)
		self.assertEqual(proc.stdout, b'FOO')


	@asynciotest
	async def test_startup(self):
		client = bl4p_plugin.BL4PClient()

		stdin = DummyReader()
		stdout = DummyWriter()
		async def stdio():
			return stdin, stdout

		stdin.buffer =  b'{"id": 0, "method": "getmanifest", "params": {}}\n\n'
		stdin.buffer += b'{"id": 1, "method": "init", "params": {"options": {"bl4p.logfile": "foo", "bl4p.dbfile": "bar"}, "configuration": {"lightning-dir": "foobar", "rpc-file": "baz"}}}\n\n'

		RPCReader = DummyReader()
		RPCWriter = DummyWriter()
		openedPaths = []
		async def open_unix_connection(path):
			openedPaths.append(path)
			return RPCReader, RPCWriter

		RPCReader.buffer = b'{"id": 0, "result": {"id": "fubar"}}\n\n'

		class BL4PInterface:
			def __init__(self, client):
				self.client = client

			async def startupInterface(self, *args):
				self.startupArgs = args

		handlers = []
		def addHandler(h):
			handlers.append(h)

		setLogFile = Mock()

		DBFiles = []
		def backendStartup(DBFile):
			DBFiles.append(DBFile)
			client.backend.configuration = MockConfiguration()

		client.messageRouter.addHandler = addHandler
		with patch.object(bl4p_plugin, 'stdio', stdio):
			with patch.object(asyncio, 'open_unix_connection', open_unix_connection):
				with patch.object(bl4p_interface, 'BL4PInterface', BL4PInterface):
					with patch.object(bl4p_plugin, 'setLogFile', setLogFile):
						with patch.object(client.backend, 'startup', backendStartup):
							await client.startup()

		call1, length = json.JSONDecoder().raw_decode(stdout.buffer.decode('UTF-8'))
		stdout.buffer = stdout.buffer[length + 2:]
		call2, length = json.JSONDecoder().raw_decode(stdout.buffer.decode('UTF-8'))
		self.assertEqual(length, len(stdout.buffer) - 2)
		self.assertEqual(call1['id'], 0)
		self.assertEqual(call2['id'], 1)
		self.assertEqual(set(call1['result'].keys()), set(['hooks', 'options', 'rpcmethods', 'subscriptions']))
		self.assertEqual(call2['result'], None)

		setLogFile.assert_called_once_with('foo')

		call, length = json.JSONDecoder().raw_decode(RPCWriter.buffer.decode('UTF-8'))
		self.assertEqual(length, len(RPCWriter.buffer) - 2)
		self.assertEqual(call, {"id": 0, "params": {}, "method": "getinfo", "jsonrpc": "2.0"})

		self.assertTrue(isinstance(client.bl4pInterface, BL4PInterface))
		self.assertEqual(client.bl4pInterface.client, client)
		self.assertEqual(client.bl4pInterface.startupArgs[:3], ('ws://localhost:8000/', '3', '3'))
		self.assertTrue(isinstance(client.bl4pInterface.startupArgs[3], secp256k1.PrivateKey))

		self.assertEqual(client.backend.LNAddress, 'fubar')
		self.assertEqual(client.backend.BL4PAddress, 'BL4Pdummy')
		self.assertEqual(DBFiles, ['bar'])

		self.assertEqual(handlers, [client.backend, client.pluginInterface, client.rpcInterface, client.bl4pInterface])


	@asynciotest
	async def test_shutdown(self):
		class MockComponent:
			def __init__(self):
				self.running = True

			async def shutdown(self):
				self.running = False

		client = bl4p_plugin.BL4PClient()
		client.backend         = MockComponent()
		client.bl4pInterface   = MockComponent()
		client.rpcInterface    = MockComponent()
		client.pluginInterface = MockComponent()

		await client.shutdown()

		self.assertFalse(client.backend.running)
		self.assertFalse(client.bl4pInterface.running)
		self.assertFalse(client.rpcInterface.running)
		self.assertFalse(client.pluginInterface.running)


	def test_messageHandling(self):
		client = bl4p_plugin.BL4PClient()

		with patch.object(client.messageRouter, 'handleMessage', Mock()) as handleMessage:
			client.handleIncomingMessage('foo')
			handleMessage.assert_called_once_with('foo')

		with patch.object(client.messageRouter, 'handleMessage', Mock()) as handleMessage:
			client.handleOutgoingMessage('foo')
			handleMessage.assert_called_once_with('foo')


	def test_terminateSignalHandler(self):
		loop = Mock()
		with patch.object(asyncio, 'get_event_loop', Mock(return_value=loop)):
			bl4p_plugin.terminateSignalHandler()
		loop.stop.assert_called_once_with()


	def test_main(self):
		calledMethods = []
		class DummyClient:
			async def startup(self):
				asyncio.ensure_future(self.task())
				calledMethods.append('startup')

			async def task(self):
				calledMethods.append('task')
				await asyncio.sleep(0.1)
				bl4p_plugin.terminateSignalHandler()

			async def shutdown(self):
				calledMethods.append('shutdown')

		signalHandlers = {}
		def add_signal_handler(sig, handler):
			signalHandlers[sig] = handler

		with patch.object(bl4p_plugin, 'BL4PClient', DummyClient) as client:
			with patch.object(asyncio.get_event_loop(), 'add_signal_handler', add_signal_handler):
				bl4p_plugin.main()

		self.assertEqual(calledMethods, ['startup', 'task', 'shutdown'])

		self.assertTrue(asyncio.get_event_loop().is_closed())

		#Allow other tests to use asyncio:
		asyncio.set_event_loop(asyncio.new_event_loop())



def stdio_process():
	import coverage
	coverage.process_startup()

	async def do_it():
		stdin, stdout = await bl4p_plugin.stdio()

		#Subsequent call must return the same:
		stdin2, stdout2 = await bl4p_plugin.stdio()
		if (stdin2, stdout2) != (stdin, stdout):
			return #refuse service

		while True:
			data = await stdin.read()
			if not data:
				break
			stdout.write(data.upper())
		await stdout.drain()

	loop = asyncio.get_event_loop()
	loop.run_until_complete(do_it())



if __name__ == '__main__':
	if sys.argv[-1] == 'stdio':
		stdio_process()
	else:
		unittest.main(verbosity=2)

