#    Copyright (C) 2019 by Bitonic B.V.
#
#    This file is part of BL4P Client.
#
#    BL4P Client is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    BL4P Client is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with BL4P Client. If not, see <http://www.gnu.org/licenses/>.

import asyncio



def asynciotest(oldMethod):
	def newMethod(self):
		loop = asyncio.get_event_loop()
		return loop.run_until_complete(oldMethod(self))

	return newMethod



class DummyWriter:
	def __init__(self):
		self.buffer = b''


	def write(self, data):
		self.buffer += data



class DummyReader:
	def __init__(self):
		self.buffer = b''


	async def read(self, n):
		ret = self.buffer[:n]
		self.buffer = self.buffer[n:]
		return ret

