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



class Bl4pApi:
	async def startup(self, url, userid, password):
		header = \
		{
		'User-Agent': 'Python Bl4pApi',
		'Authorization': userid + ':' + password,
		}
		self.websocket = await websockets.connect(
			url, extra_headers=header)
		self.task = asyncio.ensure_future(self.handleIncomingData())


	async def shutdown(self):
		self.task.cancel()
		await self.task


	async def waitFinished(self):
		await self.task


	async def handleIncomingData(self):
		try:
			try:
				while True:
					message = await self.websocket.recv()
					if message is None:
						break
					self.handleMessage(message)
			except asyncio.CancelledError:
				await self.websocket.close()
				#We're cancelled, so just quit the function
			except websockets.exceptions.ConnectionClosed:
				#TODO: maybe complain in case there are ongoing calls?
				pass #Connection closed, so just quit the function
		except:
			pass #TODO: log traceback.format_exc()


	def handleMessage(self, message):
		pass #TODO

