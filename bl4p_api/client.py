#    Copyright (C) 2018-2021 by Bitonic B.V.
#
#    This file is part of the BL4P API.
#
#    The BL4P API is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    The BL4P API is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with the BL4P API. If not, see <http://www.gnu.org/licenses/>.

import base64
import hashlib
import hmac
import websocket

from . import bl4p_pb2
from .offer import Offer
from .serialization import serialize, deserialize



class Bl4pApi:
	class Error(Exception):
		pass


	def __init__(self, url, apiKey, apiSecret):
		'''
		:param url: The websocket URL
		:param apiKey: The API key
		:param apiSecret: The base64-encoded API secret
		'''

		self.websocket = websocket.WebSocket()

		self.apiKey = apiKey
		self.apiSecret = base64.b64decode(apiSecret)
		self.websocket.connect(url)
		self.lastRequestID = 0


	def close(self):
		self.websocket.close()


	def apiCall(self, request):
		request.api_key = self.apiKey
		request.request = self.lastRequestID
		serializedRequest = serialize(request)

		signature = hmac.new(self.apiSecret, serializedRequest, hashlib.sha512).digest()

		self.websocket.send(serializedRequest + signature, opcode=websocket.ABNF.OPCODE_BINARY)

		while True:
			result = self.websocket.recv()
			result = deserialize(result)
			if result.request != self.lastRequestID:
				#TODO: log a warning (we ignore a message)
				continue

			break

		self.lastRequestID += 1


		if isinstance(result, bl4p_pb2.Error):
			#TODO: include error code
			raise Bl4pApi.Error('An error was received')

		return result


	def start(self, amount, sender_timeout_delta_ms, locked_timeout_delta_s, receiver_pays_fee):
		request = bl4p_pb2.BL4P_Start()
		request.amount.amount = amount
		request.sender_timeout_delta_ms = sender_timeout_delta_ms
		request.locked_timeout_delta_s = locked_timeout_delta_s
		request.receiver_pays_fee = receiver_pays_fee
		result = self.apiCall(request)
		return result.sender_amount.amount, result.receiver_amount.amount, result.payment_hash.data


	def selfReport(self, report, signature):
		request = bl4p_pb2.BL4P_SelfReport()
		request.report = report
		request.signature = signature
		self.apiCall(request)


	def cancelStart(self, payment_hash):
		request = bl4p_pb2.BL4P_CancelStart()
		request.payment_hash.data = payment_hash
		self.apiCall(request)


	def send(self, sender_amount, payment_hash, max_locked_timeout_delta_s, report, signature):
		request = bl4p_pb2.BL4P_Send()
		request.sender_amount.amount = sender_amount
		request.payment_hash.data = payment_hash
		request.max_locked_timeout_delta_s = max_locked_timeout_delta_s
		request.report = report
		request.signature = signature
		result = self.apiCall(request)
		return result.payment_preimage.data


	def receive(self, payment_preimage):
		request = bl4p_pb2.BL4P_Receive()
		request.payment_preimage.data = payment_preimage
		self.apiCall(request)


	def getStatus(self, payment_hash):
		request = bl4p_pb2.BL4P_GetStatus()
		request.payment_hash.data = payment_hash
		result = self.apiCall(request)
		return \
		{
		bl4p_pb2._waiting_for_selfreport: 'waiting_for_selfreport',
		bl4p_pb2._waiting_for_sender    : 'waiting_for_sender',
		bl4p_pb2._waiting_for_receiver  : 'waiting_for_receiver',
		bl4p_pb2._sender_timeout        : 'sender_timeout',
		bl4p_pb2._receiver_timeout      : 'receiver_timeout',
		bl4p_pb2._completed             : 'completed',
		bl4p_pb2._canceled              : 'canceled',
		}[result.status]


	def addOffer(self, offer):
		request = bl4p_pb2.BL4P_AddOffer()
		request.offer.CopyFrom(offer.toPB2())
		return self.apiCall(request).offerID


	def listOffers(self):
		request = bl4p_pb2.BL4P_ListOffers()
		result = self.apiCall(request)
		return \
		{
		item.offerID: Offer.fromPB2(item.offer)
		for item in result.offers
		}


	def removeOffer(self, offerID):
		request = bl4p_pb2.BL4P_RemoveOffer()
		request.offerID = offerID
		self.apiCall(request)


	def findOffers(self, query):
		request = bl4p_pb2.BL4P_FindOffers()
		request.query.CopyFrom(query.toPB2())
		result = self.apiCall(request)
		return \
		[
		Offer.fromPB2(offer_PB2)
		for offer_PB2 in result.offers
		]

