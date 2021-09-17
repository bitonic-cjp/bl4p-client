#    Copyright (C) 2019-2021 by Bitonic B.V.
#
#    This file is part of the BL4P API.
#
#    The BL4P API is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    The BL4P API is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with the BL4P API. If not, see <http://www.gnu.org/licenses/>.

import asyncio
import base64
import hashlib
import hmac
import traceback
from typing import Any, Callable, Dict, Optional
import websockets

from .offer import Offer
from .serialization import serialize, deserialize



class Bl4pApi:
	#This initialization is just to inform Mypy about data types.
	receiveTask = None #type: asyncio.Future
	sendTask    = None #type: asyncio.Future

	def __init__(self, log: Callable[[str],None] = lambda s:None) -> None:
		self.log = log #type: Callable[[str],None]
		self.lastRequestID = 0 #type: int

		self.handleResultOverride = None #type: Optional[Callable[[Any], None]]


	async def startup(self, url: str, apiKey: str, apiSecret: str) -> None:
		self.websocket = await websockets.connect(
			url) #type: websockets.WebSocketClientProtocol
		self.apiKey = apiKey.encode('utf-8') #type: bytes
		self.apiSecret = base64.b64decode(apiSecret) #type: bytes

		self.sendQueue = asyncio.Queue() #type: asyncio.Queue
		self.receiveTask = asyncio.ensure_future(self.handleIncomingData()) #type: ignore #mypy has weird ideas about ensure_future
		self.sendTask    = asyncio.ensure_future(self.sendOutgoingData()) #type: ignore #mypy has weird ideas about ensure_future


	async def shutdown(self) -> None:
		self.receiveTask.cancel()
		self.sendTask.cancel()
		await self.waitFinished()


	async def waitFinished(self) -> None:
		await self.sendTask
		await self.receiveTask


	async def handleIncomingData(self) -> None:
		try:
			try:
				while True:
					message = await self.websocket.recv() #type: Optional[bytes]
					if message is None:
						break
					result = deserialize(message) #type: Any
					try:
						if self.handleResultOverride is None:
							self.handleResult(result)
						else:
							self.handleResultOverride(result)
					except:
						self.log(traceback.format_exc())
			except asyncio.CancelledError:
				await self.websocket.close()
				#We're cancelled, so just quit the function
			except websockets.exceptions.ConnectionClosed:
				#TODO: maybe complain in case there are ongoing calls?
				pass #Connection closed, so just quit the function
		except:
			self.log(traceback.format_exc())


	async def sendOutgoingData(self) -> None:
		try:
			try:
				while True:
					message = await self.sendQueue.get() #type: bytes
					await self.websocket.send(message)
			except asyncio.CancelledError:
				pass #We're cancelled, so just quit the function
			except websockets.exceptions.ConnectionClosed:
				pass #Connection closed, so just quit the function
		except:
			self.log(traceback.format_exc())


	def handleResult(self, result: Any) -> None:
		pass #To be overloaded in derived classes


	def sendRequest(self, message: Any) -> int:
		message.request = self.lastRequestID
		self.lastRequestID += 1
		message.api_key = self.apiKey

		serializedRequest = serialize(message)
		signature = hmac.new(self.apiSecret, serializedRequest, hashlib.sha512).digest()

		#TODO: raise an exception here if the send task has stopped
		self.sendQueue.put_nowait(serializedRequest + signature)
		return message.request


	async def synCall(self, message: Any) -> Any:
		callResult = asyncio.Future() #type: asyncio.Future

		requestID = self.sendRequest(message) #type: int

		try:
			def newHandleResult(message: Any) -> None:
				assert message.request == requestID
				callResult.set_result(message)

			#Temporarily override the handleResult method to get our data:
			self.handleResultOverride = newHandleResult

			await callResult
			return callResult.result()
		finally:
			self.handleResultOverride = None

