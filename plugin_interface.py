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
from enum import Enum
import inspect
import os
import re
import settings

from json_rpc import JSONRPC
from ln_payload import Payload
from log import log, logException, setLogFile
import messages



class MethodType(Enum):
    RPCMETHOD = 0
    HOOK = 1



class OngoingRequest:
	pass #Attributes will be added on an ad-hoc basis


NO_RESPONSE = object() #Placeholder in case no response is to be sent



class PluginInterface(JSONRPC, messages.Handler):
	def __init__(self, client, inputStream, outputStream):
		JSONRPC.__init__(self, inputStream, outputStream)
		messages.Handler.__init__(self, {
			messages.LNFinish: self.sendFinish,
			messages.LNFail  : self.sendFail,
			})
		self.client = client
		self.RPCPath = None

		self.options = \
		{
		'bl4p.logfile': 'bl4p.log',
		}
		self.methods = \
		{
		'getmanifest': (self.getManifest, MethodType.RPCMETHOD),
		'init'       : (self.init       , MethodType.RPCMETHOD),

		'bl4p.getfiatcurrency'  : (self.getFiatCurrency   , MethodType.RPCMETHOD),
		'bl4p.getcryptocurrency': (self.getCryptoCurrency , MethodType.RPCMETHOD),
		'bl4p.buy'              : (self.buy               , MethodType.RPCMETHOD),
		'bl4p.sell'             : (self.sell              , MethodType.RPCMETHOD),

		'htlc_accepted'         : (self.handleHTLCAccepted, MethodType.HOOK),
		}

		def testHandler(**kwargs):
			log('Test notification received')

		self.subscriptions = {'test': testHandler}

		self.currentRequestID = None
		self.ongoingRequests = {} #ID -> (methodname, OngoingRequest)


	async def startup(self):
		#Keep handling messages until one message handler sets self.RPCPath
		#(this happens on the init message)
		while self.RPCPath is None:
			message = await self.getNextJSON()
			if message is None:
				raise Exception('Plugin interface closed before init call')
			self.handleJSON(message)

		#Start the regular message handling thread
		return JSONRPC.startup(self)


	def handleRequest(self, ID, name, params):
		self.currentRequestID = ID
		try:
			func, _ = self.methods[name]
			result = func(**params)
			if result == NO_RESPONSE:
				return
			self.sendResponse(ID, result)
		except Exception as e:
			logException()
			self.sendErrorResponse(ID,
				"Error while processing {}: {}".format(
				name, repr(e)
				))
		self.currentRequestID = None


	def storeOngoingRequest(self, name, request):
		self.ongoingRequests[self.currentRequestID] = name, request


	def findOngoingRequest(self, name, func):
		for ID, value in self.ongoingRequests.items():
			methodName, request = value
			if methodName == name and func(request):
				return ID
		raise IndexError()


	def sendOngoingRequestResponse(self, ID, result):
		#TODO: have a way to send delayed error responses
		del self.ongoingRequests[ID]
		self.sendResponse(ID, result)


	def handleNotification(self, name, params):
		func = self.subscriptions[name]
		func(**params)


	def getManifest(self, **kwargs):
		methods = []
		hooks = []
		for name, entry in self.methods.items():
			func, typ = entry
			# Skip the builtin ones, they don't get reported
			if name in ['getmanifest', 'init']:
				continue

			if typ == MethodType.HOOK:
				hooks.append(name)
				continue

			doc = inspect.getdoc(func)
			if not doc:
				self.log(
				'RPC method \'{}\' does not have a docstring.'.format(name)
				)
				doc = "Undocumented RPC method from a plugin."
				doc = re.sub('\n+', ' ', doc)

			methods.append({
				'name': name,
				'description': doc,
				})

		return {
			'options': list(self.options.values()),
			'rpcmethods': methods,
			'subscriptions': list(self.subscriptions.keys()),
			'hooks': hooks,
			}


	def init(self, options, configuration, **kwargs):
		setLogFile(options['bl4p.logfile'])

		#self.log('Plugin init got called')

		filename = configuration['rpc-file']
		lndir = configuration['lightning-dir']
		self.RPCPath = os.path.join(lndir, filename)
		#self.log('RPC path is ' + self.RPCPath)


	def getFiatCurrency(self):
		'Returns information about the fiat-currency'
		return {'name': settings.fiatName, 'divisor': settings.fiatDivisor}


	def getCryptoCurrency(self):
		'Returns information about the crypto-currency'
		return {'name': settings.cryptoName, 'divisor': settings.cryptoDivisor}


	def buy(self, limit_rate, amount, **kwargs):
		'Place an order for buying crypto-currency with fiat-currency'
		self.client.handleIncomingMessage(messages.BuyCommand(
			limitRate=limit_rate,
			amount=amount
			))


	def sell(self, limit_rate, amount, **kwargs):
		'Place an order for selling crypto-currency for fiat-currency'
		self.client.handleIncomingMessage(messages.SellCommand(
			limitRate=limit_rate,
			amount=amount
			))


	def handleHTLCAccepted(self, onion, htlc, **kwargs):
		'''
		Parameter format:
		'onion':
			{
			'hop_data':
				{
				'realm': hex,
				'per_hop': hex,
				},
			'next_onion': hex,
			'shared_secret': hex,
			},
		'htlc':
			{
			'msatoshi': int,
			'cltv_expiry': int,
			'payment_hash': hex,
			}
		'''
		realm = bytes.fromhex(onion['hop_data']['realm'])[0]
		if realm != 254: #TODO
			return {'result': 'continue'} #it's not handled by us

		try:
			paymentHash = bytes.fromhex(htlc['payment_hash'])
			payload = Payload.decode(
				bytes.fromhex(onion['hop_data']['per_hop']))
			cryptoAmount = htlc['msatoshi']
			CLTVExpiryDelta = htlc['cltv_expiry'], #TODO: check if this is a relative or absolute value. For now, relative is used everywhere.
		except:
			log('Refused incoming transaction because there is something wrong with it:')
			logException()
			return {'result': 'fail'}

		#We will have to send a response later, possibly after finishing this function
		req = OngoingRequest()
		req.paymentHash = paymentHash
		self.storeOngoingRequest('htlc_accepted', req)

		self.client.handleIncomingMessage(messages.LNIncoming(
			paymentHash = paymentHash,
			cryptoAmount = cryptoAmount,
			CLTVExpiryDelta = CLTVExpiryDelta,
			fiatAmount = payload.fiatAmount,
			offerID = payload.offerID,
			))

		#Don't send a response now:
		#either it was already sent by the LNIncoming handler,
		#or we will send it later.
		return NO_RESPONSE


	def sendFinish(self, message):
		ID = self.findOngoingRequest('htlc_accepted',
			lambda x: x.paymentHash == message.paymentHash)

		self.sendOngoingRequestResponse(ID, {
			'result': 'resolve',
			'payment_key': message.paymentPreimage.hex(),
			})


	def sendFail(self, message):
		ID = self.findOngoingRequest('htlc_accepted',
			lambda x: x.paymentHash == message.paymentHash)

		self.sendOngoingRequestResponse(ID, {
			'result': 'fail',
			})

