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
import order



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
					await asyncio.sleep(1)
					self.initiateOfferSearch()
			except asyncio.CancelledError:
				pass #We're cancelled, so just quit the function
		except:
			log('Exception in Trader:')
			logException()


	def handleIncomingMessage(self, message):
		{
		messages.BL4PFindOffersResult : self.handleBL4PFindOffersResult,
		}[message.__class__](message)


	def initiateOfferSearch(self):
		for o in self.client.backend.getOrders():
			#Only query for idle transactions:
			if o.status != order.STATUS_IDLE:
				continue

			self.client.handleOutgoingMessage(
				messages.BL4PFindOffers(query=o)
				)


	def handleBL4PFindOffersResult(self, message):
		localID = message.request.query.ID

		if not message.offers: #found no matching offers
			localOrder = self.client.backend.getOrder(localID)

			if localOrder.remoteOfferID is not None:
				#No matching offers and we're already published:
				#do nothing
				return

			log('Found no offers - making our own')
			self.client.handleOutgoingMessage(
				messages.BL4PAddOffer(offer=localOrder)
				)
			#Note: the reply is sent to Backend
			return

		log('Found offers - starting a transaction')
		#TODO: filter on sensibility (e.g. max >= min for all conditions)
		#TODO: check if offers actually match
		#TODO: filter counterOffers on acceptability
		#TODO: sort counterOffers (e.g. on exchange rate)

		#Start trade on the first in the list
		self.client.backend.startTransaction(localID, message.offers[0])

