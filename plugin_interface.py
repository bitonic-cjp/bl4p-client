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
from log import log, logException
import messages



class MethodType(Enum):
    RPCMETHOD = 0
    HOOK = 1



class PluginInterface(JSONRPC):
	def __init__(self, client, inputStream, outputStream):
		JSONRPC.__init__(self, inputStream, outputStream)
		self.client = client
		self.RPCPath = None

		self.options = {}
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


	async def startup(self):
		#Keep handling messages until one message handler sets self.RPCPath
		#(this happens on the init message)
		while self.RPCPath is None:
			message = await self.getNextMessage()
			if message is None:
				raise Exception('Plugin interface closed before init call')
			self.handleMessage(message)

		#Start the regular message handling thread
		return JSONRPC.startup(self)


	def handleRequest(self, ID, name, params):
		try:
			func, _ = self.methods[name]
			result = func(**params)
			self.sendResponse(ID, result)
		except Exception as e:
			logException()
			self.sendErrorResponse(ID,
				"Error while processing {}: {}".format(
				name, repr(e)
				))


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
				'per_hop': hex
				'short_channel_id': str,
				'amt_to_forward': int,
				'outgoing_cltv_value': int,
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
		log('handleHTLCAccepted got called')

