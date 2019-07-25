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

from typing import Callable, Dict, List, Optional, Type, Union, cast

from simplestruct import Struct

from bl4p_api import offer as _offer



class PluginCommand(Struct):
	commandID = None #type: Optional[int]


class BuyCommand(PluginCommand):
	amount    = 0 #type: int
	limitRate = 0 #type: int


class SellCommand(PluginCommand):
	amount    = 0 #type: int
	limitRate = 0 #type: int


class ListCommand(PluginCommand):
	pass


class PluginCommandResult(Struct):
	commandID = 0    #type: int
	result    = None #type: Dict[str, str]


class BL4PRequest(Struct):
	localOrderID = 0 #type: int #not transmitted - for local use only


class BL4PStart(BL4PRequest):
	amount                  = 0    #type: int
	sender_timeout_delta_ms = 0    #type: int
	locked_timeout_delta_s  = 0    #type: int
	receiver_pays_fee       = True #type: bool


class BL4PCancelStart(BL4PRequest):
	paymentHash = b'' #type: bytes


class BL4PSend(BL4PRequest):
	amount                     = 0    #type: int
	paymentHash                = b''  #type: bytes
	max_locked_timeout_delta_s = 0    #type: int


class BL4PReceive(BL4PRequest):
	paymentPreimage = b'' #type: bytes


class BL4PAddOffer(BL4PRequest):
	offer = None #type: _offer.Offer


class BL4PRemoveOffer(BL4PRequest):
	offerID = 0 #type: int


class BL4PFindOffers(BL4PRequest):
	query = None #type: _offer.Offer


class BL4PResult(Struct):
	request = None #type: BL4PRequest


class BL4PStartResult(BL4PResult):
	senderAmount   = 0   #type: int
	receiverAmount = 0   #type: int
	paymentHash    = b'' #type: bytes


class BL4PCancelStartResult(BL4PResult):
	pass


class BL4PSendResult(BL4PResult):
	paymentPreimage = b'' #type: bytes


class BL4PReceiveResult(BL4PResult):
	pass


class BL4PAddOfferResult(BL4PResult):
	ID = 0 #type: int


class BL4PRemoveOfferResult(BL4PResult):
	pass


class BL4PFindOffersResult(BL4PResult):
	offers = [] #type: List[_offer.Offer]


class BL4PError(BL4PResult):
	pass


class LNPay(Struct):
	localOrderID          = 0 #type: int #not transmitted - for local use only

	destinationNodeID     = ''  #type: str
	paymentHash           = b'' #type: bytes
	recipientCryptoAmount = 0   #type: int
	maxSenderCryptoAmount = 0   #type: int
	minCLTVExpiryDelta    = 0   #type: int
	fiatAmount            = 0   #type: int
	offerID               = 0   #type: int


class LNIncoming(Struct):
	paymentHash     = b'' #type: bytes
	cryptoAmount    = 0   #type: int
	CLTVExpiryDelta = 0   #type: int
	fiatAmount      = 0   #type: int
	offerID         = 0   #type: int


class LNFinish(Struct):
	paymentHash     = b'' #type: bytes
	paymentPreimage = b'' #type: bytes


class LNFail(Struct):
	paymentHash = b'' #type: bytes


class LNPayResult(Struct):
	localOrderID       = 0    #type: int

	senderCryptoAmount = 0    #type: int
	paymentHash        = b''  #type: bytes
	paymentPreimage    = None #type: Optional[bytes] #None indicates a failed payment


AnyMessage = Union[
	BuyCommand,
	SellCommand,
	ListCommand,
	PluginCommandResult,
	BL4PStart,
	BL4PCancelStart,
	BL4PSend,
	BL4PReceive,
	BL4PAddOffer,
	BL4PRemoveOffer,
	BL4PFindOffers,
	BL4PStartResult,
	BL4PCancelStartResult,
	BL4PSendResult,
	BL4PReceiveResult,
	BL4PAddOfferResult,
	BL4PRemoveOfferResult,
	BL4PFindOffersResult,
	BL4PError,
	LNPay,
	LNIncoming,
	LNFinish,
	LNFail,
	LNPayResult,
	]

AnyMessageHandler = Union[
	Callable[[BuyCommand], None],
	Callable[[SellCommand], None],
	Callable[[ListCommand], None],
	Callable[[PluginCommandResult], None],
	Callable[[BL4PStart], None],
	Callable[[BL4PCancelStart], None],
	Callable[[BL4PSend], None],
	Callable[[BL4PReceive], None],
	Callable[[BL4PAddOffer], None],
	Callable[[BL4PRemoveOffer], None],
	Callable[[BL4PFindOffers], None],
	Callable[[BL4PStartResult], None],
	Callable[[BL4PCancelStartResult], None],
	Callable[[BL4PSendResult], None],
	Callable[[BL4PReceiveResult], None],
	Callable[[BL4PAddOfferResult], None],
	Callable[[BL4PRemoveOfferResult], None],
	Callable[[BL4PFindOffersResult], None],
	Callable[[BL4PError], None],
	Callable[[LNPay], None],
	Callable[[LNIncoming], None],
	Callable[[LNFinish], None],
	Callable[[LNFail], None],
	Callable[[LNPayResult], None],
	]



class Handler:
	def __init__(self, handlerMethods: Dict[type, AnyMessageHandler] = {}) -> None:
		self.handlerMethods = handlerMethods #type: Dict[type, AnyMessageHandler]


	def handleMessage(self, message: AnyMessage) -> None:
		handler = cast(Callable[[AnyMessage], None], self.handlerMethods[message.__class__])
		handler(message)



class Router(Handler):
	def addHandler(self, handler: Handler) -> None:
		for msgClass, method in handler.handlerMethods.items():
			if msgClass in self.handlerMethods:
				raise Exception(
					'Router: cannot have multiple handlers for a single message class')
			self.handlerMethods[msgClass] = method

