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
import json
import re
import sys
import traceback



class MethodType(Enum):
    RPCMETHOD = 0
    HOOK = 1



class PluginInterface:
	def __init__(self):
		self.options = {}
		self.methods = {}
		self.subscriptions = {}
		self.addMethod("getmanifest", self.getManifest)


	def startup(self, stdin, stdout):
		self.stdin = stdin
		self.stdout = stdout
		self.task = asyncio.ensure_future(self.handleIncomingData())


	async def shutdown(self):
		self.task.cancel()
		await self.task


	async def handleIncomingData(self):
		try:
			try:
				sys.stderr.write('Started plugin interface\n')
				inputBuffer = b''
				while True:
					newData = await self.stdin.readline()
					inputBuffer += newData
					messages = inputBuffer.split(b'\n\n')

					for msg in messages[:-1]:
						self.handleMessageData(msg)
					inputBuffer = messages[-1] #the remaining data

					if not newData: #EOF
						return
			except asyncio.CancelledError:
				pass #We're cancelled, so just quit the function
		except:
			sys.stderr.write('Exception in plugin interface:\n')
			sys.stderr.write(traceback.format_exc())


	def log(self, s):
		pass #TODO


	def handleMessageData(self, msg):
		msg = msg.decode('UTF-8')
		request = json.loads(msg)

		# If this has an 'id'-field, it's a request and returns a
		# result. Otherwise it's a notification and it doesn't
		# return anything.
		if 'id' in request:
			self.handleRequest(request)
		else:
			self.handleNotification(request)


	def handleRequest(self, request):
		name = request['method']

		func, _ = self.methods[name]
		params = request['params']

		try:
			result = {
			'jsonrpc': '2.0',
			'id': request['id'],
			'result': func(*params)
			}
		except Exception as e:
			result = {
			'jsonrpc': '2.0',
			'id': request['id'],
			"error": "Error while processing {}: {}".format(
			request['method'], repr(e)
			),
			}
			self.log(traceback.format_exc())
		result = json.dumps(result)
		self.stdout.write(result.encode('UTF-8') + b'\n\n')


	def handleNotification(self, notification):
		return #TODO


	def addMethod(self, name, func):
		self.methods[name] = (func, MethodType.RPCMETHOD)


	def getManifest(self):
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

