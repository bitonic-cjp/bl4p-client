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

import asyncio
import os
import signal
import socket
import time
import traceback

from json_rpc import JSONRPC



class RPCInterface(JSONRPC):
	def __init__(self, node, inputStream, outputStream):
		JSONRPC.__init__(self, inputStream, outputStream)
		self.node = node


	def handleRequest(self, ID, name, params):
		self.node.handleRPCCall(self, ID, name, params)


	def handleNotification(self, name, params):
		self.node.pluginInterface.sendNotification(name, params)



class PluginInterface(JSONRPC):
	def __init__(self, node, inputStream, outputStream):
		JSONRPC.__init__(self, inputStream, outputStream)
		self.node = node
		self.manifest = None


	async def startup(self):
		#print('PluginInterface startup')
		self.manifest = await self.synCall('getmanifest')
		self.methods = [m['name'] for m in self.manifest['rpcmethods']]
		#print(manifest)

		await self.synCall('init',
			{
			'options': {},
			'configuration': \
				{
				'lightning-dir': self.node.directory,
				'rpc-file'     : self.node.RPCFile,
				}
			})

		return JSONRPC.startup(self)


	def handleResult(self, ID, result):
		resultCB, errorCB = self.node.pluginResultCallbacks[ID]
		del self.node.pluginResultCallbacks[ID]
		resultCB(result)


	def handleError(self, ID, error):
		resultCB, errorCB = self.node.pluginResultCallbacks[ID]
		del self.node.pluginResultCallbacks[ID]
		errorCB(error)



class Node:
	def __init__(self, nodeID, RPCFile):
		self.nodeID = nodeID

		abspath = os.path.abspath(RPCFile)
		self.directory, self.RPCFile = os.path.split(abspath)

		self.pluginResultCallbacks = {} #ID -> (function(result), function(error))


	async def startup(self):
		try:
			os.remove(self.RPCFile)
		except FileNotFoundError:
			pass #it's ok
		self.rpc = await asyncio.start_unix_server(
			client_connected_cb=self.RPCConnection,
			path=self.RPCFile
			)

		self.pluginProcess = await asyncio.create_subprocess_exec(
			'./bl4p_plugin.py',
			stdin=asyncio.subprocess.PIPE,
			stdout=asyncio.subprocess.PIPE,
			stderr=None, #Inherited
			)

		self.pluginInterface = PluginInterface(self,
			self.pluginProcess.stdout, self.pluginProcess.stdin)
		await self.pluginInterface.startup()


	async def RPCConnection(self, reader, writer):
		#print('Lightning: Got incoming RPC connection')
		interface = RPCInterface(self, reader, writer)
		interface.startup()
		await interface.waitFinished()
		#print('Lightning: Ended RPC connection')


	async def shutdown(self):
		await self.pluginInterface.shutdown()
		self.pluginProcess.kill()
		await self.pluginProcess.wait()


	def handleRPCCall(self, interface, ID, name, params):
		#Plugin RPC pass-through:
		if name in self.pluginInterface.methods:
			outgoingID = self.pluginInterface.sendRequest(name, params)

			def resultCB(result):
				#print(result)
				interface.sendResponse(ID, result)

			def errorCB(error):
				#print(error)
				interface.sendErrorResponse(ID, error)

			self.pluginResultCallbacks[outgoingID] = (resultCB, errorCB)
			return

		#Own methods
		method = \
		{
		'getinfo': self.getInfo,
		'getroute': self.getRoute,
		}[name]
		#TODO: exception handling
		result = method(**params)
		interface.sendResponse(ID, result)


	def getInfo(self, **kwargs):
		return {'id': self.nodeID}


	def getRoute(self, id, msatoshi, cltv, **kwargs):
		return {'route': []} #TODO



nodes = \
[
	Node(nodeID='node0', RPCFile='node0-rpc'),
	Node(nodeID='node1', RPCFile='node1-rpc'),
]



async def startup():
	#print('Starting nodes')
	for n in nodes:
		await n.startup()


async def shutdown():
	#print('Shutting down nodes')
	for n in nodes:
		await n.shutdown()


def terminateSignalHandler():
	#print('Got signal to terminate')
	loop = asyncio.get_event_loop()
	loop.stop()


loop = asyncio.get_event_loop()

loop.run_until_complete(startup())

loop.add_signal_handler(signal.SIGINT , terminateSignalHandler)
loop.add_signal_handler(signal.SIGTERM, terminateSignalHandler)
loop.run_forever()

loop.run_until_complete(shutdown())
loop.close()

