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
import json
import sys
import traceback



class JSONRPC:
	def __init__(self, inputStream, outputStream):
		self.inputStream = inputStream
		self.outputStream = outputStream

		self.inputBuffer = b''
		self.outgoingRequestID = 0
		self.decoder = json.JSONDecoder()


	def startup(self):
		self.task = asyncio.ensure_future(self.handleIncomingData())


	async def shutdown(self):
		self.task.cancel()
		await self.task


	async def waitFinished(self):
		await self.task


	async def handleIncomingData(self):
		self.log('Started JSON RPC')
		try:
			try:
				while True:
					message = await self.getNextMessage()
					if message is None:
						break
					self.handleMessage(message)
			except asyncio.CancelledError:
				pass #We're cancelled, so just quit the function
			except BrokenPipeError:
				pass #Pipe closed, so just quit the function
		except:
			self.log('Exception in JSON RPC:')
			self.log(traceback.format_exc())
		self.log('Stopped JSON RPC')


	async def getNextMessage(self):
		while True:
			try:
				#self.log('Input buffer: ' + str(self.inputBuffer))
				request, length = self.decoder.raw_decode(self.inputBuffer.decode("UTF-8"))
			except ValueError:
				#probably the buffer is incomplete
				newData = await self.inputStream.read(1024)
				if not newData: #EOF
					return None
				self.inputBuffer += newData
				continue

			#self.log('Request: ' + str(request))
			#TODO: length in chars may be different from length in bytes
			self.inputBuffer = self.inputBuffer[length:].lstrip()
			return request


	def handleMessage(self, request):
		#self.log('Handling incoming message: ' + str(request))
		try:
			if 'error' in request:
				self.handleError(request['id'], request['error'])
			elif 'result' in request:
				self.handleResult(request['id'], request['result'])
			elif 'id' in request:
				self.handleRequest(request['id'], request['method'], request['params'])
			else:
				self.handleNotification(request['method'], request['params'])
		except Exception:
			self.log(traceback.format_exc())


	def writeJSON(self, msg):
		msg = json.dumps(msg)
		self.outputStream.write(msg.encode('UTF-8') + b'\n\n')


	def log(self, s):
		#TODO
		sys.stderr.write(s + '\n')


	async def synCall(self, name, params=[]):
		ID = self.sendRequest(name, params)
		while True:
			message = await self.getNextMessage()
			if 'result' in message and 'id' in message and message['id'] == ID:
				break #it's ours
			#Generic processing of messages that are not ours
			self.handleMessage(message)
		return message['result']


	def sendRequest(self, name, params=[]):
		ID = self.outgoingRequestID
		self.outgoingRequestID += 1
		msg = {'id': ID, 'method': name, 'params': params}
		self.writeJSON(msg)
		return ID


	def sendResponse(self, ID, result):
		response = \
			{
			'jsonrpc': '2.0',
			'id': ID,
			'result': result
			}
		self.writeJSON(response)


	def sendErrorResponse(self, ID, error):
		response = \
			{
			'jsonrpc': '2.0',
			'id': ID,
			"error": error,
			}
		self.writeJSON(response)


	def sendNotification(self, name, params):
		msg = {'method': name, 'params': params}
		self.writeJSON(msg)


	def handleRequest(self, ID, name, params):
		pass #To be overloaded in derived classes


	def handleNotification(self, name, params):
		pass #To be overloaded in derived classes


	def handleResult(self, ID, result):
		pass #To be overloaded in derived classes


	def handleError(self, ID, error):
		pass #To be overloaded in derived classes

