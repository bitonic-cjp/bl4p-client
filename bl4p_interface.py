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

from bl4p_api import bl4p_pb2
from bl4p_api import asynclient as bl4p
from bl4p_api import offer
from log import log
import messages



class BL4PInterface(bl4p.Bl4pApi):
	def __init__(self, client):
		bl4p.Bl4pApi.__init__(self, log=log)
		self.client = client
		self.activeRequests = {}


	def sendOutgoingMessage(self, message):
		if isinstance(message, messages.BL4PAddOffer):
			request = bl4p_pb2.BL4P_AddOffer()
			request.offer.CopyFrom(message.offer.toPB2())
		elif isinstance(message, messages.BL4PFindOffers):
			request = bl4p_pb2.BL4P_FindOffers()
			request.query.CopyFrom(message.query.toPB2())
		else:
			raise Exception('BL4PInterface cannot send message ' + str(message))
		log('BL4PInterface: Sending request: ' + str(request))
		requestID = self.sendRequest(request)
		self.activeRequests[requestID] = message


	def handleResult(self, result):
		log('BL4PInterface: Received result: ' + str(result))
		if isinstance(result, bl4p_pb2.BL4P_AddOfferResult):
			message = messages.BL4PAddOfferResult(
				ID=result.offerID,
				)
		elif isinstance(result, bl4p_pb2.BL4P_FindOffersResult):
			message = messages.BL4PFindOffersResult(offers = \
				[
				offer.Offer.fromPB2(offer_PB2)
				for offer_PB2 in result.offers
				])
		else:
			log('Ignoring unrecognized message type from BL4P: ' + \
				str(result.__class__))
			return

		message.request = self.activeRequests[result.request]
		del self.activeRequests[result.request]
		self.client.handleIncomingMessage(message)

