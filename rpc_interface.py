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

import struct

from json_rpc import JSONRPC
from log import log
import messages
import settings



class Payload:
	@staticmethod
	def decode(data):
		fiatAmount, offerID = struct.unpack('!QI', data)
		return Payload(fiatAmount, offerID)

	def __init__(self, fiatAmount, offerID):
		self.fiatAmount = fiatAmount
		self.offerID = offerID


	def encode(self):
		return struct.pack('!QI', self.fiatAmount, self.offerID)



class RPCInterface(JSONRPC):
	def __init__(self, client, inputStream, outputStream):
		JSONRPC.__init__(self, inputStream, outputStream)
		self.client = client

		self.nodeID = None

		self.ongoingRequests = {} #ID -> (methodname, message)


	async def startup(self):
		info = await self.synCall('getinfo')
		self.nodeID = info['id']

		return JSONRPC.startup(self)


	def sendStoredRequest(self, message, name, params):
		ID = self.sendRequest(name, params)
		self.ongoingRequests[ID] = (name, message)


	def handleResult(self, ID, result):
		name, message = self.ongoingRequests[ID]
		del self.ongoingRequests[ID]
		self.handleStoredRequestResult(message, name, result)


	def sendOutgoingMessage(self, message):
		if isinstance(message, messages.LNPay):
			self.sendStoredRequest(message, 'getroute',
				{
				    "id": message.destinationNodeID,
				    "msatoshi": message.recipientCryptoAmount,
				    "riskfactor": 1,
				    "cltv": message.minCLTVExpiryDelta,
				})
			#TODO: we called getroute, but that is no guarantee we
			#will have an outgoing transaction (we might crash
			#before sendpay succeeds).
			#Make sure the LNPay message stays stored!
		else:
			raise Exception('RPCInterface cannot send message ' + str(message))


	def handleStoredRequestResult(self, message, name, result):
		messageClass = message.__class__

		if (name, messageClass) == ('getroute', messages.LNPay):
			log('Got getroute results')

			route = result['route']

			payload = Payload(message.fiatAmount, message.offerID)

			#TODO: check maxSenderCryptoAmount

			#TODO: include payload and set realm number
			self.sendStoredRequest(message, 'sendpay',
				{
				    "route": route,
				    "payment_hash": message.paymentHash,
				    #"description": description, #Is this useful for the payload?
				    "msatoshi": message.recipientCryptoAmount,
				})
		elif (name, messageClass) == ('sendpay', messages.LNPay):
			pass #TODO: maybe check if sendpay was OK
		else:
			raise Exception('RPCInterface made an error in storing requests')


	def handleError(self, ID, error):
		pass #TODO

