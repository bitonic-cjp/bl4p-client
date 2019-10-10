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
from typing import Any, Dict, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
	import bl4p_plugin #pragma: nocover

from json_rpc import JSONRPC
from ln_payload import Payload
from log import log
import messages
import settings


class extendedLNPayMessage(messages.LNPay):
	senderCryptoAmount    = 0   #type: int



class RPCInterface(JSONRPC, messages.Handler):
	def __init__(self, client: 'bl4p_plugin.BL4PClient', inputStream: asyncio.StreamReader, outputStream: asyncio.StreamWriter) -> None:
		JSONRPC.__init__(self, inputStream, outputStream)
		messages.Handler.__init__(self, {
			messages.LNPay: self.sendPay,
			})
		self.client = client #type: bl4p_plugin.BL4PClient

		self.nodeID = None #type: str

		self.ongoingRequests = {} #type: Dict[int, Tuple[str, messages.AnyMessage]] #ID -> (methodname, message)


	async def startupRPC(self) -> None:
		info = await self.synCall('getinfo') #type: Dict
		self.nodeID = info['id']

		JSONRPC.startup(self)


	def sendStoredRequest(self, message: messages.AnyMessage, name: str, params: Dict[str, Any]) -> None:
		ID = self.sendRequest(name, params) #type: int
		self.ongoingRequests[ID] = (name, message)


	def handleResult(self, ID: int, result: Any) -> None:
		name = None #type: str
		message = None #type: messages.AnyMessage
		name, message = self.ongoingRequests[ID]
		del self.ongoingRequests[ID]
		self.handleStoredRequestResult(message, name, result)


	def handleError(self, ID: int, code: int, message: str) -> None:
		name = None #type: str
		storedMessage = None #type: messages.AnyMessage
		name, storedMessage = self.ongoingRequests[ID]
		del self.ongoingRequests[ID]
		self.handleStoredRequestError(storedMessage, name, code)


	def sendPay(self, message: messages.LNPay) -> None:
		#TODO (bug 4): check if we're already sending out funds on this
		#payment hash.
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


	def handleStoredRequestResult(self, message: messages.AnyMessage, name: str, result: Dict[str, Any]):
		#We depend on C-Lightning to pass the expected types in result

		messageClass = message.__class__ #type: type

		if (name, messageClass) == ('getroute', messages.LNPay):
			assert isinstance(message, messages.LNPay) #mypy is stupid

			route = result['route'] #type: List[Dict[str, Any]]

			newMessage = extendedLNPayMessage(
				localOrderID          = message.localOrderID,
				destinationNodeID     = message.destinationNodeID,
				paymentHash           = message.paymentHash,
				recipientCryptoAmount = message.recipientCryptoAmount,
				maxSenderCryptoAmount = message.maxSenderCryptoAmount,
				minCLTVExpiryDelta    = message.minCLTVExpiryDelta,
				fiatAmount            = message.fiatAmount,
				offerID               = message.offerID,

				senderCryptoAmount    = route[0]["msatoshi"]
				)

			if newMessage.senderCryptoAmount > message.maxSenderCryptoAmount:
				#TODO: proper handling of this
				raise Exception('maxSenderCryptoAmount exceeded')

			payload = Payload(message.fiatAmount, message.offerID) #type: Payload

			self.sendStoredRequest(newMessage, 'sendpay',
				{
				'route': route,
				'payment_hash': newMessage.paymentHash.hex(),
				'msatoshi': newMessage.recipientCryptoAmount,

				'realm': 254, #TODO
				'data': payload.encode().hex(),
				})
		elif (name, messageClass) == ('sendpay', extendedLNPayMessage):
			assert isinstance(message, extendedLNPayMessage) #mypy is stupid

			#TODO: maybe check if sendpay was OK
			self.sendStoredRequest(message, 'waitsendpay',
				{
				'payment_hash': message.paymentHash.hex(),
				})
		elif (name, messageClass) == ('waitsendpay', extendedLNPayMessage):
			assert isinstance(message, extendedLNPayMessage) #mypy is stupid

			assert result['status'] == 'complete' #TODO: what else?
			paymentPreimage = bytes.fromhex(result['payment_preimage']) #type: bytes
			self.client.handleIncomingMessage(messages.LNPayResult(
				localOrderID = message.localOrderID,

				senderCryptoAmount = message.senderCryptoAmount,
				paymentHash = message.paymentHash,
				paymentPreimage = paymentPreimage,
				))
		else:
			raise Exception('RPCInterface made an error in storing requests')


	def handleStoredRequestError(self, message: messages.AnyMessage, name: str, error: int) -> None:
		messageClass = message.__class__ #type: type

		if (name, messageClass, error) == ('waitsendpay', extendedLNPayMessage, 203):
			assert isinstance(message, extendedLNPayMessage) #mypy is stupid

			#Recipient refused the transaction
			self.client.handleIncomingMessage(messages.LNPayResult(
				localOrderID = message.localOrderID,

				senderCryptoAmount = message.senderCryptoAmount,
				paymentHash = message.paymentHash,
				paymentPreimage = None, #indicates error
				))
		else:
			log('Received an unhandled error from a Lightning RPC call!!!')

