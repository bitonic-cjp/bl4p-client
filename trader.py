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

from log import log, logException



class Trader:
	def __init__(self, client):
		self.client = client


	def startup(self):
		self.task = asyncio.ensure_future(self.discoverOfferMatches())


	async def shutdown(self):
		self.task.cancel()
		await self.task


	async def waitFinished(self):
		await self.task


	async def discoverOfferMatches(self):
		try:
			try:
				while True:
					await asyncio.sleep(10)
					log('10 seconds done')
			except asyncio.CancelledError:
				pass #We're cancelled, so just quit the function
		except:
			log('Exception in Trader:')
			logException()


