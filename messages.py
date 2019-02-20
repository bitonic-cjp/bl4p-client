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

from simplestruct import Struct



class BuyCommand(Struct):
	amount = 0
	limitRate = 0


class SellCommand(Struct):
	amount = 0
	limitRate = 0


class BL4PStart(Struct):
	localTransactionID = 0 #not transmitted - for local use only

	amount = 0
	sender_timeout_delta_ms = 0
	locked_timeout_delta_s = 0
	receiver_pays_fee = True


class BL4PSend(Struct):
	localTransactionID = 0 #not transmitted - for local use only

	amount = 0
	paymentHash = b''


class BL4PAddOffer(Struct):
	offer = None


class BL4PFindOffers(Struct):
	query = None


class BL4PResult(Struct):
	request = None


class BL4PStartResult(BL4PResult):
	senderAmount = 0
	receiverAmount = 0
	paymentHash = b''


class BL4PSendResult(BL4PResult):
	paymentPreimage = b''


class BL4PAddOfferResult(BL4PResult):
	ID = 0


class BL4PFindOffersResult(BL4PResult):
	offers = []


class LNPay(Struct):
	destinationNodeID = ''
	paymentHash = b''
	recipientCryptoAmount = 0
	maxSenderCryptoAmount = 0
	minCLTVExpiryDelta = 0
	fiatAmount = 0
	offerID = 0


class LNIncoming(Struct):
	paymentHash = b''
	cryptoAmount = 0
	CLTVExpiryDelta = 0
	fiatAmount = 0
	offerID = 0



class Handler:
	def __init__(self, handlerMethods={}):
		self.handlerMethods = handlerMethods


	def handleMessage(self, message):
		return self.handlerMethods[message.__class__](message)



class Router(Handler):
	def addHandler(self, handler):
		for msgClass, method in handler.handlerMethods.items():
			if msgClass in self.handlerMethods:
				raise Exception(
					'Router: cannot have multiple handlers for a single message class')
			self.handlerMethods[msgClass] = method

