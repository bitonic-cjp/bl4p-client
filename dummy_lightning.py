#!/usr/bin/env python3
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
import json
import logging
import os
import signal
import socket
import struct
import time
import traceback

from json_rpc import JSONRPC
from simplestruct import Struct



CURRENT_BLOCK_HEIGHT = 1234567



class Transaction(Struct):
	sourceID        = ''
	destID          = ''
	source_msatoshi = 0
	dest_msatoshi   = 0
	sourceCLTV      = 0
	destCLTV        = 0
	paymentHash     = '' #hex
	paymentPreimage = '' #hex
	data            = '' #hex



def decodeLegacyPayload(payload):
	payload = bytes.fromhex(payload)
	realm = payload[0]
	assert realm == 0
	msatoshi, cltv_value = struct.unpack('>QI', payload[9:21])
	return \
	{
	'msatoshi'  : msatoshi,
	'cltv_value': cltv_value,
	}


class RPCInterface(JSONRPC):
	def __init__(self, node, inputStream, outputStream):
		JSONRPC.__init__(self, inputStream, outputStream)
		self.node = node


	def handleRequest(self, ID, name, params):
		logging.info('%s RPC <== %d %s %s' % (self.node.nodeID, ID, name, params))
		self.node.handleRPCCall(self, ID, name, params)


	def handleNotification(self, name, params):
		self.node.pluginInterface.sendNotification(name, params)


	def sendResponse(self, ID, result):
		logging.info('%s RPC ==> %d %s' % (self.node.nodeID, ID, result))
		return JSONRPC.sendResponse(self, ID, result)


	def sendErrorResponse(self, ID, code, message):
		logging.info('%s RPC ==> %d ERROR %d: %s' % (self.node.nodeID, ID, code, message))
		return JSONRPC.sendErrorResponse(self, ID, code, message)



class PluginInterface(JSONRPC):
	def __init__(self, node, inputStream, outputStream):
		JSONRPC.__init__(self, inputStream, outputStream)
		self.node = node
		self.manifest = None


	async def startup(self, options):
		logging.debug('%s > PluginInterface startup' % self.node.nodeID)
		self.manifest = await self.synCall('getmanifest')
		self.methods = [m['name'] for m in self.manifest['rpcmethods']]
		self.hooks = self.manifest['hooks'][:]

		logging.debug('%s Received manifest; calling init' % self.node.nodeID)

		await self.synCall('init',
			{
			'options': options,
			'configuration': \
				{
				'lightning-dir': self.node.directory,
				'rpc-file'     : self.node.RPCFile,
				}
			})

		logging.debug('%s < PluginInterface startup' % self.node.nodeID)

		return JSONRPC.startup(self)


	def handleResult(self, ID, result):
		logging.info('%s plugin <== %d %s' % (self.node.nodeID, ID, result))
		resultCB, errorCB = self.node.pluginResultCallbacks[ID]
		del self.node.pluginResultCallbacks[ID]
		resultCB(result)


	def handleError(self, ID, code, message):
		logging.info('%s plugin <== %d ERROR %d: %s' % (self.node.nodeID, ID, code, message))
		resultCB, errorCB = self.node.pluginResultCallbacks[ID]
		del self.node.pluginResultCallbacks[ID]
		errorCB(code, message)


	def sendRequest(self, name, params={}):
		ID = JSONRPC.sendRequest(self, name, params)
		logging.info('%s plugin ==> %d %s %s' % (self.node.nodeID, ID, name, params))
		return ID



NO_RESPONSE = object() #Placeholder in case no response is to be sent
DELAYED_RESPONSE = object() #Placeholder in case a delayed response is to be sent



class Node:
	def __init__(self, nodeID, RPCFile, bl4pLogFile, bl4pDBFile):
		self.nodeID = nodeID

		abspath = os.path.abspath(RPCFile)
		self.directory, self.RPCFile = os.path.split(abspath)

		self.bl4pLogFile = bl4pLogFile
		self.bl4pDBFile = bl4pDBFile

		self.startupFinished = False

		self.pluginResultCallbacks = {} #ID -> (function(result), function(code, message))

		#This is for RPC calls that have started, but for which no return data
		#has been sent yet:
		self.ongoingRequests = {} #ID -> (interface, methodname, metadata)

		#Is set to the request ID if we're inside an RPC call
		self.currentRequestID = None

		#This is for payments that have finished/failed, but for which
		#waitsendpay was not yet called:
		self.unprocessedPaymentResults = {} #paymentHash -> paymentPreimage or None


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
			self.pluginProcess.stdout, self.pluginProcess.stdin,
			)
		await self.pluginInterface.startup({
			'bl4p.logfile': self.bl4pLogFile,
			'bl4p.dbfile': self.bl4pDBFile,
			})
		self.startupFinished = True


	async def RPCConnection(self, reader, writer):
		#print('Lightning: Got incoming RPC connection')
		interface = RPCInterface(self, reader, writer)
		interface.startup()
		await interface.waitFinished()
		#print('Lightning: Ended RPC connection')


	async def shutdown(self):
		await self.pluginInterface.shutdown()
		self.pluginProcess.terminate()
		await self.pluginProcess.wait()


	def findOngoingRequest(self, name, func):
		'''
		Return the ID of an ongoing request
		name: the name of the called function
		func: a function evaluating the metadata of the request
		'''
		for ID, value in self.ongoingRequests.items():
			interface, methodName, metadata = value
			if methodName == name and func(metadata):
				return ID
		raise IndexError()


	def setOngoingRequestAttribute(self, name, value):
		self.ongoingRequests[self.currentRequestID][2][name] = value


	def sendDelayedResponse(self, ID, result):
		'''
		Send a response for an ongoing  request,
		and remove the ongoing request, as it is now finished.
		'''
		interface = self.ongoingRequests[ID][0]
		del self.ongoingRequests[ID]
		interface.sendResponse(ID, result)


	def sendDelayedErrorResponse(self, ID, code, message):
		'''
		Send an error response for an ongoing  request,
		and remove the ongoing request, as it is now finished.
		'''
		interface = self.ongoingRequests[ID][0]
		del self.ongoingRequests[ID]
		interface.sendErrorResponse(ID, code, message)


	def handleRPCCall(self, interface, ID, name, params):
		self.currentRequestID = ID
		try:
			#Plugin RPC pass-through:
			if name in self.pluginInterface.methods:
				outgoingID = self.pluginInterface.sendRequest(name, params)

				def resultCB(result):
					#print(result)
					interface.sendResponse(ID, result)

				def errorCB(code, message):
					#print(code, message)
					interface.sendErrorResponse(ID, code, message)

				self.pluginResultCallbacks[outgoingID] = (resultCB, errorCB)
				return

			#Own methods
			method = \
			{
			'getinfo': self.getInfo,
			'getroute': self.getRoute,
			'createonion': self.createOnion,
			'sendonion': self.sendOnion,
			'waitsendpay': self.waitSendPay,
			}[name]

			self.ongoingRequests[ID] = interface, name, {}

			#TODO: exception handling
			result = method(**params)

			if result not in (NO_RESPONSE, DELAYED_RESPONSE):
				interface.sendResponse(ID, result)
			if result != DELAYED_RESPONSE and ID in self.ongoingRequests:
				del self.ongoingRequests[ID]
		finally:
			self.currentRequestID = None


	def getInfo(self, **kwargs):
		return {'id': self.nodeID, 'blockheight': CURRENT_BLOCK_HEIGHT}


	def getRoute(self, id, msatoshi, cltv, **kwargs):
		route = \
		[
		{
			'msatoshi': int(1.01*msatoshi), #simulated 1% fee
			'delay': cltv + 100, #simulated 10 hops, 10 blocks per hop
			'id': 'ID of some intermediate node',
			'channel': '12345x10x2',
			'style': 'legacy',
		},
		{
			'msatoshi': msatoshi,
			'delay': cltv,
			'id': id,
			'channel': '54321x25x1',
			'style': 'legacy',
		},
		]
		return {'route': route}


	def createOnion(self, hops, assocdata, **kwargs):
		assert len(hops) > 0
		assert hops[-1]['pubkey'] != self.nodeID

		#Just a serialized version of the arguments:		
		onion = json.dumps([hops, assocdata]).encode('utf-8').hex()
		shared_secrets = ['Secret 1', 'Secret 2']

		return {'onion': onion, 'shared_secrets': shared_secrets}


	def sendOnion(self, onion, first_hop, payment_hash, label, shared_secrets, msatoshi, **kwargs):
		hops, payment_hash = json.JSONDecoder().raw_decode(bytes.fromhex(onion).decode('utf-8'))[0]

		logging.debug('sendOnion: hops = ' + str(hops))

		last_hop = decodeLegacyPayload(hops[-2]['payload']) #actually second-last in hops list

		tx = Transaction(
			sourceID = self.nodeID,
			destID   = hops[-1]['pubkey'],
			source_msatoshi = first_hop['msatoshi'],
			dest_msatoshi   = last_hop['msatoshi'],
			sourceCLTV = CURRENT_BLOCK_HEIGHT + first_hop['delay'],
			destCLTV   = last_hop['cltv_value'],
			paymentHash = payment_hash,
			paymentPreimage = None,
			data = hops[-1]['payload'],
			)

		global nodes
		try:
			nodes[tx.destID].handleIncomingTransaction(tx)
		except:
			logging.exception('Failing the LN transaction because of this exception:')
			self.finishOutgoingTransaction(tx.paymentHash, None)


	def waitSendPay(self, payment_hash):

		#This attribute will be used in finishOutgoingTransaction, either
		#as called here (if the result is already in), or, if the result
		#arrives later, whenever the result arrives.
		self.setOngoingRequestAttribute('paymentHash', payment_hash)

		if payment_hash in self.unprocessedPaymentResults:
			#The result is already in:
			result = self.unprocessedPaymentResults[payment_hash]
			del self.unprocessedPaymentResults[payment_hash]
			self.finishOutgoingTransaction(payment_hash, result)

			#Response was already sent by finishOutgoingTransaction
			return NO_RESPONSE

		#Response will be sent later by finishOutgoingTransaction
		return DELAYED_RESPONSE


	def handleIncomingTransaction(self, tx):
		if not self.startupFinished:
			raise Exception(
				'Got an incoming transaction but initialization is not yet finished')

		assert 'htlc_accepted' in self.pluginInterface.hooks

		ID = self.pluginInterface.sendRequest('htlc_accepted', {
			'onion':
				{
				'payload': tx.data,
				},
			'htlc':
				{
				'amount': str(tx.dest_msatoshi) + 'msat',
				'cltv_expiry': tx.destCLTV, #TODO: check if this is a relative or absolute value. For now, relative is used everywhere.
				'payment_hash': tx.paymentHash,
				}
			})

		def resultCB(result):
			global nodes

			if result['result'] == 'resolve':
				tx.paymentPreimage = result['payment_key']
				nodes[tx.sourceID].finishOutgoingTransaction(tx.paymentHash, tx.paymentPreimage)
			elif result['result'] == 'fail':
				nodes[tx.sourceID].finishOutgoingTransaction(tx.paymentHash, None)
			#TODO: handle continue

		def errorCB(code, message):
			print(code, message) #TODO

		self.pluginResultCallbacks[ID] = (resultCB, errorCB)



	def finishOutgoingTransaction(self, paymentHash, paymentResult):
		try:
			ID = self.findOngoingRequest('waitsendpay', lambda x: x['paymentHash'] == paymentHash)
		except IndexError:
			#waitsendpay was not yet called - store results for
			#whenever it does get called
			self.unprocessedPaymentResults[paymentHash] = paymentResult
			return

		#Send the response to waitsendpay
		if paymentResult is None:
			self.sendDelayedErrorResponse(ID,
				203, #Permanent failure at destination
				'Transaction was refused'
				)
		else:
			self.sendDelayedResponse(ID,
				{
				'status': 'complete',
				'payment_preimage': paymentResult,
				})



nodes = \
{
	'node0': Node(nodeID='node0', RPCFile='node0-rpc', bl4pLogFile='node0.bl4p.log', bl4pDBFile='node0.bl4p.db'),
	'node1': Node(nodeID='node1', RPCFile='node1-rpc', bl4pLogFile='node1.bl4p.log', bl4pDBFile='node1.bl4p.db'),
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



logging.basicConfig(
	format = '%(asctime)s %(levelname)s: %(message)s',
	level = logging.INFO,
	)

loop = asyncio.get_event_loop()

loop.run_until_complete(startup())

loop.add_signal_handler(signal.SIGINT , terminateSignalHandler)
loop.add_signal_handler(signal.SIGTERM, terminateSignalHandler)
loop.run_forever()

loop.run_until_complete(shutdown())
loop.close()

