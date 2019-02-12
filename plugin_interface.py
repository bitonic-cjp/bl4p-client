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
import sys
import traceback



class PluginInterface:
	def __init__(self):
		pass


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
						await self.handleMessageData(msg)
					inputBuffer = messages[-1] #the remaining data

					if not newData: #EOF
						return
			except asyncio.CancelledError:
				pass #We're cancelled, so just quit the function
		except:
			sys.stderr.write('Exception in plugin interface:\n')
			sys.stderr.write(traceback.format_exc())


	async def handleMessageData(self, msg):
		self.stdout.write(b'Got input: %s\n' % msg)
		await self.stdout.drain()


