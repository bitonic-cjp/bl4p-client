#    Copyright (C) 2019 by Bitonic B.V.
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
import traceback
import websockets

from .offer import Offer
from .serialization import serialize, deserialize



class Bl4pApi:
	def __init__(self, log=lambda s:None):
		self.log = log
		self.lastRequestID = 0


	async def startup(self, url, userid, password):
		header = \
		{
		'User-Agent': 'Python Bl4pApi',
		'Authorization': userid + ':' + password,
		}
		self.websocket = await websockets.connect(
			url, extra_headers=header)

		self.sendQueue = asyncio.Queue()
		self.receiveTask = asyncio.ensure_future(self.handleIncomingData())
		self.sendTask    = asyncio.ensure_future(self.sendOutgoingData())


	async def shutdown(self):
		self.receiveTask.cancel()
		self.sendTask.cancel()
		await self.waitFinished()


	async def waitFinished(self):
		await self.sendTask
		await self.receiveTask


	async def handleIncomingData(self):
		try:
			try:
				while True:
					message = await self.websocket.recv()
					if message is None:
						break
					result = deserialize(message)
					try:
						self.handleResult(result)
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


	async def sendOutgoingData(self):
		try:
			try:
				while True:
					message = await self.sendQueue.get()
					await self.websocket.send(message)
			except asyncio.CancelledError:
				pass #We're cancelled, so just quit the function
			except websockets.exceptions.ConnectionClosed:
				pass #Connection closed, so just quit the function
		except:
			self.log(traceback.format_exc())


	def handleResult(self, result):
		pass #To be overloaded in derived classes


	def sendRequest(self, message):
		message.request = self.lastRequestID
		self.lastRequestID += 1

		#TODO: raise an exception here if the send task has stopped
		self.sendQueue.put_nowait(serialize(message))
		return message.request


	async def synCall(self, message):
		callResult = asyncio.Future()

		requestID = self.sendRequest(message)

		oldhandleResult = self.handleResult
		try:
			def newHandleResult(message):
				assert message.request == requestID
				callResult.set_result(message)

			#Temporarily hack the handleResult method to get our data:
			self.handleResult = newHandleResult

			await callResult
			return callResult.result()
		finally:
			self.handleResult = oldhandleResult

