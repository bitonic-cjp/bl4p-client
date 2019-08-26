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
from typing import Any, Dict

import decodedbuffer
from log import log, logException



#DoS prevention measure:
MAX_BUFFER_LENGTH = 1024*1024 #type: int



class JSONRPC:
	def __init__(self, inputStream: asyncio.StreamReader, outputStream: asyncio.StreamWriter) -> None:
		self.inputStream = inputStream #type: asyncio.StreamReader
		self.outputStream = outputStream #type: asyncio.StreamWriter

		self.inputBuffer = decodedbuffer.DecodedBuffer('UTF-8') #type: decodedbuffer.DecodedBuffer
		self.outgoingRequestID = 0 #type: int
		self.decoder = json.JSONDecoder() #type: json.JSONDecoder


	def startup(self) -> None:
		self.task = None #type: asyncio.Future
		self.task = asyncio.ensure_future(self.handleIncomingData()) #type: ignore #mypy has weird ideas about ensure_future


	async def shutdown(self) -> None:
		self.task.cancel()
		await self.task


	async def waitFinished(self) -> None:
		await self.task


	async def handleIncomingData(self) -> None:
		#log('Started JSON RPC')
		try:
			try:
				while True:
					message = await self.getNextJSON() #type: Dict
					if message is None:
						break
					self.handleJSON(message)
			except asyncio.CancelledError:
				pass #We're cancelled, so just quit the function
			except BrokenPipeError:
				pass #Pipe closed, so just quit the function
		except:
			log('Exception in JSON RPC:')
			logException()
		#log('Stopped JSON RPC')


	async def getNextJSON(self) -> Dict:
		while True:
			try:
				#log('Input buffer: ' + self.inputBuffer.get())
				request = None #type: Dict
				length  = None #type: int
				request, length = self.decoder.raw_decode(self.inputBuffer.get())
				assert type(request) == dict #TODO: unit test
			except ValueError:
				#probably the buffer is incomplete
				newData = await self.inputStream.read(1024) #type: bytes
				if not newData: #EOF
					return None
				self.inputBuffer.append(newData)
				if len(self.inputBuffer.get()) > MAX_BUFFER_LENGTH:
					log('JSON RPC error: maximum buffer length exceeded. We\'re probably not receiving valid JSON.')
					self.inputBuffer = decodedbuffer.DecodedBuffer('UTF-8') #replace with empty buffer
					raise Exception('Maximum receive buffer length exceeded - throwing away data')
				continue

			self.inputBuffer.set(self.inputBuffer.get()[length:].lstrip())

			#log('<-- ' + str(request))
			return request


	def handleJSON(self, request: Any) -> None:
		try:
			ID     = None #type: int
			error  = None #type: str
			result = None #type: Any
			method = None #type: str
			params = None #type: Dict

			if 'error' in request:
				ID    = request['id']
				error = request['error']
				assert type(ID)    == int #TODO: unit test
				assert type(error) == str #TODO: unit test
				self.handleError(ID, error)
			elif 'result' in request:
				ID     = request['id']
				result = request['result']
				assert type(ID) == int #TODO: unit test
				#result can be any type
				self.handleResult(ID, result)
			elif 'id' in request:
				ID     = request['id']
				method = request['method']
				params = request['params']
				assert type(ID)     == int #TODO: unit test
				assert type(method) == str #TODO: unit test
				assert type(params) == dict #TODO: unit test
				self.handleRequest(ID, method, params)
			else:
				method = request['method']
				params = request['params']
				assert type(method) == str #TODO: unit test
				assert type(params) == dict #TODO: unit test
				self.handleNotification(method, params)
		except Exception: #TODO: remove (let the main task terminate)
			logException()


	def writeJSON(self, msg: Dict) -> None:
		#log('--> ' + str(msg))
		JSONMessage = json.dumps(msg) #type: str
		self.outputStream.write(JSONMessage.encode('UTF-8') + b'\n\n')


	async def synCall(self, name: str, params: Dict = {}) -> Any:
		ID = self.sendRequest(name, params) #type: int
		while True:
			message = await self.getNextJSON() #type: Dict

			#These are ours:
			if 'result' in message and 'id' in message and message['id'] == ID:
				break
			if 'error' in message and 'id' in message and message['id'] == ID:
				raise Exception(message['error'])

			#Generic processing of messages that are not ours
			self.handleJSON(message)
		return message['result']


	def sendRequest(self, name: str, params: Dict = {}) -> int:
		ID = self.outgoingRequestID #type: int
		self.outgoingRequestID += 1
		msg = \
		{
			'jsonrpc': '2.0',
			'id': ID,
			'method': name,
			'params': params,
		} #type: Dict
		self.writeJSON(msg)
		return ID


	def sendResponse(self, ID: int, result: Any) -> None:
		response = \
			{
			'jsonrpc': '2.0',
			'id': ID,
			'result': result,
			} #type: Dict
		self.writeJSON(response)


	def sendErrorResponse(self, ID: int, error: str) -> None:
		response = \
			{
			'jsonrpc': '2.0',
			'id': ID,
			"error": error,
			} #type: Dict
		self.writeJSON(response)


	def sendNotification(self, name: str, params: Dict) -> None:
		msg = \
		{
			'jsonrpc': '2.0',
			'method': name,
			'params': params,
		} #type: Dict
		self.writeJSON(msg)


	def handleRequest(self, ID: int, name: str, params: Dict) -> None:
		pass #To be overloaded in derived classes


	def handleNotification(self, name: str, params: Dict) -> None:
		pass #To be overloaded in derived classes


	def handleResult(self, ID: int, result: Any) -> None:
		pass #To be overloaded in derived classes


	def handleError(self, ID: int, error: str) -> None:
		pass #To be overloaded in derived classes

