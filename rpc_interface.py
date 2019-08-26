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

from typing import Any, Dict

from json_rpc import JSONRPC
from ln_payload import Payload
from log import log
import messages
import settings



class RPCInterface(JSONRPC, messages.Handler):
	def __init__(self, client, inputStream, outputStream):
		JSONRPC.__init__(self, inputStream, outputStream)
		messages.Handler.__init__(self, {
			messages.LNPay: self.sendPay,
			})
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


	def handleResult(self, ID: int, result: Any) -> None:
		name, message = self.ongoingRequests[ID]
		del self.ongoingRequests[ID]
		self.handleStoredRequestResult(message, name, result)


	def handleError(self, ID: int, error: str) -> None:
		name, message = self.ongoingRequests[ID]
		del self.ongoingRequests[ID]
		self.handleStoredRequestError(message, name, error)


	def sendPay(self, message):
		#TODO: check if we're already sending out funds on this payment hash.
		#This can be the case, for instance, after a restart.

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


	def handleStoredRequestResult(self, message, name, result):
		messageClass = message.__class__

		if (name, messageClass) == ('getroute', messages.LNPay):
			route = result['route']

			message.senderCryptoAmount = route[0]["msatoshi"]
			if message.senderCryptoAmount > message.maxSenderCryptoAmount:
				#TODO: proper handling of this
				raise Exception('maxSenderCryptoAmount exceeded')

			payload = Payload(message.fiatAmount, message.offerID)

			self.sendStoredRequest(message, 'sendpay',
				{
				'route': route,
				'payment_hash': message.paymentHash.hex(),
				'msatoshi': message.recipientCryptoAmount,

				'realm': 254, #TODO
				'data': payload.encode().hex(),
				})
		elif (name, messageClass) == ('sendpay', messages.LNPay):
			#TODO: maybe check if sendpay was OK
			self.sendStoredRequest(message, 'waitsendpay',
				{
				'payment_hash': message.paymentHash.hex(),
				})
		elif (name, messageClass) == ('waitsendpay', messages.LNPay):
			assert result['status'] == 'complete' #TODO: what else?
			paymentPreimage = bytes.fromhex(result['payment_preimage'])
			self.client.handleIncomingMessage(messages.LNPayResult(
				localOrderID = message.localOrderID,

				senderCryptoAmount = message.senderCryptoAmount,
				paymentHash = message.paymentHash,
				paymentPreimage = paymentPreimage,
				))
		else:
			raise Exception('RPCInterface made an error in storing requests')


	def handleStoredRequestError(self, message, name, error):
		messageClass = message.__class__

		if (name, messageClass, error) == ('waitsendpay', messages.LNPay, 203):
			#Recipient refused the transaction
			self.client.handleIncomingMessage(messages.LNPayResult(
				localOrderID = message.localOrderID,

				senderCryptoAmount = message.senderCryptoAmount,
				paymentHash = message.paymentHash,
				paymentPreimage = None, #indicates error
				))
		else:
			log('Received an unhandled error from a Lightning RPC call!!!')

