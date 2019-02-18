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


	def sendOutgoingMessage(self, message):
		if isinstance(message, messages.LNPay):
			log('LNPay message arrived at RPCInterface')
			#payload = Payload(message.fiatAmount, message.offerID)
			#destinationNodeID
			#paymentHash
			#recipientCryptoAmount
			#maxSenderCryptoAmount
			#minCLTVExpiryDelta
			#self.sendRequest('pay', params=[])
		else:
			raise Exception('RPCInterface cannot send message ' + str(message))


	def handleResult(self, ID, result):
		pass #TODO


	def handleError(self, ID, error):
		pass #TODO

