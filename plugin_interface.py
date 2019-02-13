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
import traceback

from json_rpc import JSONRPC


class MethodType(Enum):
    RPCMETHOD = 0
    HOOK = 1



class PluginInterface(JSONRPC):
	def __init__(self, inputStream, outputStream):
		JSONRPC.__init__(self, inputStream, outputStream)

		self.options = {}
		self.methods = \
		{
		'getmanifest': (self.getManifest, MethodType.RPCMETHOD),
		'init'       : (self.init       , MethodType.RPCMETHOD),

		'bl4p.getfiatcurrency'  : (self.getFiatCurrency  , MethodType.RPCMETHOD),
		'bl4p.getcryptocurrency': (self.getCryptoCurrency, MethodType.RPCMETHOD),
		'bl4p.buy'              : (self.buy              , MethodType.RPCMETHOD),
		'bl4p.sell'             : (self.sell             , MethodType.RPCMETHOD),
		}

		def testHandler(*args):
			self.log('Test notification received')

		self.subscriptions = {'test': testHandler}


	def handleRequest(self, ID, name, params):
		try:
			func, _ = self.methods[name]
			result = func(*params)
			self.sendResponse(ID, result)
		except Exception as e:
			self.log(traceback.format_exc())
			self.sendErrorResponse(ID,
				"Error while processing {}: {}".format(
				name, repr(e)
				))


	def handleNotification(self, name, params):
		func = self.subscriptions[name]
		func(*params)


	def getManifest(self, *args):
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


	def init(self, options, configuration, *args):
		self.log('Plugin init got called')

		filename = configuration['rpc-file']
		lndir = configuration['lightning-dir']
		self.RPCPath = os.path.join(lndir, filename)
		self.log('RPC path is ' + self.RPCPath)


	def getFiatCurrency(self):
		'Returns information about the fiat-currency'
		return {'name': settings.fiatName, 'divisor': settings.fiatDivisor}


	def getCryptoCurrency(self):
		'Returns information about the crypto-currency'
		return {'name': settings.cryptoName, 'divisor': settings.cryptoDivisor}


	def buy(self, limitRate, amount):
		'Place an order for buying crypto-currency with fiat-currency'
		pass #TODO


	def sell(self, limitRate, amount):
		'Place an order for selling crypto-currency for fiat-currency'
		pass #TODO

