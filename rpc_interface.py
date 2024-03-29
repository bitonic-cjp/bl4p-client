#!/usr/bin/env python3
#    Copyright (C) 2019-2021 by Bitonic B.V.
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
import logging
from typing import Any, Dict, List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
	import bl4p_plugin #pragma: nocover

from json_rpc import JSONRPC
from ln_payload import Payload
import messages
import onion_utils
import settings



class extendedLNPayMessage(messages.LNPay):
	senderCryptoAmount    = 0   #type: int
	route                 = []  #type: List[Dict[str, Any]]



class RPCInterface(JSONRPC, messages.Handler):
	def __init__(self, client: 'bl4p_plugin.BL4PClient', inputStream: asyncio.StreamReader, outputStream: asyncio.StreamWriter) -> None:
		JSONRPC.__init__(self, inputStream, outputStream)
		messages.Handler.__init__(self, {
			messages.LNPay: self.sendPay,
			})
		self.client = client #type: bl4p_plugin.BL4PClient
		self.ongoingRequests = {} #type: Dict[int, Tuple[str, messages.AnyMessage]] #ID -> (methodname, message)


	async def startupRPC(self) -> None:
		info = await self.synCall('getinfo') #type: Dict
		self.nodeID = info['id'] #type: str

		JSONRPC.startup(self)


	def sendStoredRequest(self, message: messages.AnyMessage, name: str, params: Dict[str, Any]) -> None:
		ID = self.sendRequest(name, params) #type: int
		self.ongoingRequests[ID] = (name, message)


	def handleResult(self, ID: int, result: Any) -> None:
		name, message = self.ongoingRequests[ID] #type: Tuple[str, messages.AnyMessage]
		del self.ongoingRequests[ID]
		self.handleStoredRequestResult(message, name, result)


	def handleError(self, ID: int, code: int, message: str) -> None:
		name, storedMessage = self.ongoingRequests[ID] #type: Tuple[str, messages.AnyMessage]
		logging.error('Received an error for call ID = %d, name = %s, message = %s' % \
			(ID, name, str(storedMessage)))
		logging.error('Error code = %d, message = %s' % (code, message))
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

			#TODO: handle getroute failures

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

				senderCryptoAmount    = route[0]['msatoshi'],
				route                 = route,
				) #type: extendedLNPayMessage

			if newMessage.senderCryptoAmount > message.maxSenderCryptoAmount:
				#TODO: proper handling of this
				raise Exception('maxSenderCryptoAmount exceeded')
			#TODO: check for message.minCLTVExpiryDelta

			self.sendStoredRequest(newMessage, 'getinfo', {})

		elif (name, messageClass) == ('getinfo', extendedLNPayMessage):
			assert isinstance(message, extendedLNPayMessage) #mypy is stupid

			#TODO: check if getinfo was OK

			blockHeight = result['blockheight']

			payload = Payload(message.fiatAmount, message.offerID) #type: Payload

			onionHopsData = onion_utils.makeCreateOnionHopsData(
				message.route, payload.encode(), blockHeight) #type: List[Dict[str, Any]]

			self.sendStoredRequest(message, 'createonion',
				{
				'hops': onionHopsData,
				'assocdata': message.paymentHash.hex(),
				})

		elif (name, messageClass) == ('createonion', extendedLNPayMessage):
			assert isinstance(message, extendedLNPayMessage) #mypy is stupid

			#TODO: check if createonion was OK

			self.sendStoredRequest(message, 'sendonion',
				{
				'onion':          result['onion'],
				'first_hop':      message.route[0],
				'payment_hash':   message.paymentHash.hex(),
				'label':          'BL4P payment',
				'shared_secrets': result['shared_secrets'],
				'msatoshi':       message.recipientCryptoAmount,
				})

		elif (name, messageClass) == ('sendonion', extendedLNPayMessage):
			assert isinstance(message, extendedLNPayMessage) #mypy is stupid

			#TODO: check if sendonion was OK

			self.sendStoredRequest(message, 'waitsendpay',
				{
				'payment_hash': message.paymentHash.hex(),
				})

		elif (name, messageClass) == ('waitsendpay', extendedLNPayMessage):
			assert isinstance(message, extendedLNPayMessage) #mypy is stupid

			#TODO: check if waitsendpay was OK

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
			logging.error('Received an unhandled error from a Lightning RPC call!!!')

