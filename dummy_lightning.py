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
from simplestruct import Struct



class Transaction(Struct):
	sourceID        = ''
	destID          = ''
	source_msatoshi = 0
	dest_msatoshi   = 0
	sourceCLTV      = 0
	destCLTV        = 0
	paymentHash     = '' #hex
	paymentPreimage = '' #hex
	realm           = 0
	data            = '' #hex



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
		self.hooks = self.manifest['hooks'][:]
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
		'sendpay': self.sendPay,
		}[name]
		#TODO: exception handling
		result = method(**params)
		interface.sendResponse(ID, result)


	def getInfo(self, **kwargs):
		return {'id': self.nodeID}


	def getRoute(self, id, msatoshi, cltv, **kwargs):
		route = \
		[
		{
			'msatoshi': int(1.01*msatoshi), #simulated 1% fee
			'delay': cltv + 100, #simulated 10 hops, 10 blocks per hop
			'id': 'ID of some intermediate node',
		},
		{
			'msatoshi': msatoshi,
			'delay': cltv,
			'id': id,
		},
		]
		return {'route': route}


	def sendPay(self, route, payment_hash, msatoshi, realm, data, **kwargs):
		#TODO: realm, data is a fantasy interface, not yet in lightningd

		assert len(route) > 0
		assert route[-1]['id'] != self.nodeID
		assert route[-1]['msatoshi'] == msatoshi

		tx = Transaction(
			sourceID = self.nodeID,
			destID   = route[-1]['id'],
			source_msatoshi = route[ 0]['msatoshi'],
			dest_msatoshi   = route[-1]['msatoshi'],
			sourceCLTV = route[ 0]['delay'],
			destCLTV   = route[-1]['delay'],
			paymentHash = payment_hash,
			paymentPreimage = None,
			realm = realm,
			data = data,
			)

		global nodes
		nodes[tx.destID].handleIncomingTransaction(tx)


	def handleIncomingTransaction(self, tx):
		assert 'htlc_accepted' in self.pluginInterface.hooks

		#TODO: per_hop is a fantasy interface, not yet in lightningd
		ID = self.pluginInterface.sendRequest('htlc_accepted', {
			'onion':
				{
				'hop_data':
					{
					'realm': bytes([tx.realm]).hex(),
					'per_hop': tx.data,
					},
				},
			'htlc':
				{
				'msatoshi': tx.dest_msatoshi,
				'cltv_expiry': tx.destCLTV, #TODO: check if this is a relative or absolute value. For now, relative is used everywhere.
				'payment_hash': tx.paymentHash,
				}
			})

		def resultCB(result):
			global nodes

			if result['result'] == 'resolve':
				tx.paymentPreimage = result['payment_key']
				nodes[tx.sourceID].finishOutgoingTransaction(tx)
			#TODO: handle fail and continue

		def errorCB(error):
			print(error) #TODO

		self.pluginResultCallbacks[ID] = (resultCB, errorCB)


	def finishOutgoingTransaction(self, tx):
		print('finishOutgoingTransaction called')



nodes = \
{
	'node0': Node(nodeID='node0', RPCFile='node0-rpc'),
	'node1': Node(nodeID='node1', RPCFile='node1-rpc'),
}



async def startup():
	#print('Starting nodes')
	for n in nodes.values():
		await n.startup()


async def shutdown():
	#print('Shutting down nodes')
	for n in nodes.values():
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

