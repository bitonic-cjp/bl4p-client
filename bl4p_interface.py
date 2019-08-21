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

from typing import Any, Dict, TYPE_CHECKING

from bl4p_api import bl4p_pb2
from bl4p_api import asynclient as bl4p
from bl4p_api import offer

if TYPE_CHECKING:
	import bl4p_plugin

from log import log
import messages



class BL4PInterface(bl4p.Bl4pApi, messages.Handler):
	def __init__(self, client: 'bl4p_plugin.BL4PClient') -> None:
		bl4p.Bl4pApi.__init__(self, log=log)
		messages.Handler.__init__(self, {
			messages.BL4PStart      : self.sendStart,
			messages.BL4PCancelStart: self.sendCancelStart,
			messages.BL4PSend       : self.sendSend,
			messages.BL4PReceive    : self.sendReceive,
			messages.BL4PAddOffer   : self.sendAddOffer,
			messages.BL4PRemoveOffer: self.sendRemoveOffer,
			messages.BL4PFindOffers : self.sendFindOffers,
			})
		self.client = client #type: bl4p_plugin.BL4PClient
		self.activeRequests = {} #type: Dict[int, messages.BL4PRequest]


	async def startup(self, url: str, userid: str, password: str) -> None:
		await bl4p.Bl4pApi.startup(self, url, userid, password)

		#Get our currently active orders
		result = await self.synCall(bl4p_pb2.BL4P_ListOffers()) #type: bl4p_pb2.BL4P_ListOffersResult
		#TODO: runtime check that result is actually bl4p_pb2.BL4P_ListOffersResult

		#Remove them one by one.
		#When appropriate, they will be re-added later.
		for item in result.offers:
			log('Removing offer that existed before startup with ID ' + str(item.offerID))
			request = bl4p_pb2.BL4P_RemoveOffer() #type: bl4p_pb2.BL4P_RemoveOffer
			request.offerID = item.offerID
			await self.synCall(request)


	def sendStart(self, message: messages.BL4PStart) -> None:
		request = bl4p_pb2.BL4P_Start() #type: bl4p_pb2.BL4P_Start
		request.amount.amount = message.amount
		request.sender_timeout_delta_ms = message.sender_timeout_delta_ms
		request.locked_timeout_delta_s = message.locked_timeout_delta_s
		request.receiver_pays_fee = message.receiver_pays_fee
		requestID = self.sendRequest(request) #type: int
		self.activeRequests[requestID] = message


	def sendCancelStart(self, message: messages.BL4PCancelStart) -> None:
		request = bl4p_pb2.BL4P_CancelStart() #type: bl4p_pb2.BL4P_CancelStart
		request.payment_hash.data = message.paymentHash
		requestID = self.sendRequest(request) #type: int
		self.activeRequests[requestID] = message


	def sendSend(self, message: messages.BL4PSend) -> None:
		request = bl4p_pb2.BL4P_Send() #type: bl4p_pb2.BL4P_Send
		request.sender_amount.amount = message.amount
		request.payment_hash.data = message.paymentHash
		request.max_locked_timeout_delta_s = message.max_locked_timeout_delta_s
		requestID = self.sendRequest(request) #type: int
		self.activeRequests[requestID] = message


	def sendReceive(self, message: messages.BL4PReceive) -> None:
		request = bl4p_pb2.BL4P_Receive() #type: bl4p_pb2.BL4P_Receive
		request.payment_preimage.data = message.paymentPreimage
		requestID = self.sendRequest(request)
		self.activeRequests[requestID] = message


	def sendAddOffer(self, message: messages.BL4PAddOffer) -> None:
		request = bl4p_pb2.BL4P_AddOffer() #type: bl4p_pb2.BL4P_AddOffer
		request.offer.CopyFrom(message.offer.toPB2())
		requestID = self.sendRequest(request) #type: int
		self.activeRequests[requestID] = message


	def sendRemoveOffer(self, message: messages.BL4PRemoveOffer) -> None:
		request = bl4p_pb2.BL4P_RemoveOffer() #type: bl4p_pb2.BL4P_RemoveOffer
		request.offerID = message.offerID
		requestID = self.sendRequest(request)
		self.activeRequests[requestID] = message


	def sendFindOffers(self, message: messages.BL4PFindOffers) -> None:
		request = bl4p_pb2.BL4P_FindOffers() #type: bl4p_pb2.BL4P_FindOffers
		request.query.CopyFrom(message.query.toPB2())
		requestID = self.sendRequest(request)
		self.activeRequests[requestID] = message


	def handleResult(self, result: Any) -> None:
		#log('BL4PInterface: Received result: ' + str(result))

		request = self.activeRequests[result.request] #type: messages.BL4PRequest
		message = None #type: messages.BL4PResult

		if isinstance(result, bl4p_pb2.BL4P_StartResult):
			message = messages.BL4PStartResult(
				request = request,
				senderAmount = result.sender_amount.amount,
				receiverAmount = result.receiver_amount.amount,
				paymentHash = result.payment_hash.data
				)
		elif isinstance(result, bl4p_pb2.BL4P_CancelStartResult):
			message = messages.BL4PCancelStartResult(
				request = request,
				)
		elif isinstance(result, bl4p_pb2.BL4P_SendResult):
			message = messages.BL4PSendResult(
				request = request,
				paymentPreimage = result.payment_preimage.data,
				)
		elif isinstance(result, bl4p_pb2.BL4P_ReceiveResult):
			message = messages.BL4PReceiveResult(
				request = request,
				)
		elif isinstance(result, bl4p_pb2.BL4P_AddOfferResult):
			message = messages.BL4PAddOfferResult(
				request = request,
				ID=result.offerID,
				)
		elif isinstance(result, bl4p_pb2.BL4P_RemoveOfferResult):
			message = messages.BL4PRemoveOfferResult(
				request = request,
				)
		elif isinstance(result, bl4p_pb2.BL4P_FindOffersResult):
			message = messages.BL4PFindOffersResult(
				request = request,
				offers = \
				[
				offer.Offer.fromPB2(offer_PB2)
				for offer_PB2 in result.offers
				])

		elif isinstance(result, bl4p_pb2.Error):
			log('Got BL4P error (reason = %d)' % result.reason)
			message = messages.BL4PError(
				request = request,
				)

		else:
			log('Ignoring unrecognized message type from BL4P: ' + \
				str(result.__class__))
			return

		del self.activeRequests[result.request]
		self.client.handleIncomingMessage(message)


