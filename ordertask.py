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
import messages



class OrderTask:
	def __init__(self, client, orderID):
		self.client = client
		self.orderID = orderID
		self.callResult = None


	def startup(self):
		self.task = asyncio.ensure_future(self.doTrading())


	async def shutdown(self):
		self.task.cancel()
		await self.task


	async def waitFinished(self):
		await self.task


	def setCallResult(self, result):
		self.callResult.set_result(result)


	async def doTrading(self):
		try:
			await self.doOfferSearch()
		except asyncio.CancelledError:
			pass #We're cancelled, so just quit the function
		except:
			log('Exception in order task:')
			logException()


	async def doOfferSearch(self):
		order = self.client.backend.getOrder(self.orderID)
		while True: #TODO: quit once the order is finished
			queryResult = await self.call(messages.BL4PFindOffers(query=order))

			if queryResult.offers: #found a matching offer
				log('Found offers - starting a transaction')
				#TODO: filter on sensibility (e.g. max >= min for all conditions)
				#TODO: check if offers actually match
				#TODO: filter counterOffers on acceptability
				#TODO: sort counterOffers (e.g. on exchange rate)

				#Start trade on the first in the list
				self.client.backend.startTransaction(self.orderID, queryResult.offers[0])
				return

			if order.remoteOfferID is None:
				log('Found no offers - making our own')
				self.client.handleOutgoingMessage(
					messages.BL4PAddOffer(offer=order)
					)
				#Note: the reply is sent to Backend

			await asyncio.sleep(1)



	async def call(self, message):
		self.client.handleOutgoingMessage(message)
		self.callResult = asyncio.Future()
		await self.callResult
		return self.callResult.result()

