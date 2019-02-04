#    Copyright (C) 2019 by Bitonic B.V.
#
#    This file is part of BL4P client.
#
#    BL4P client is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    BL4P client is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with BL4P client. If not, see <http://www.gnu.org/licenses/>.

import struct



class Payload:
	@staticmethod
	def decode(data):
		fiatAmount = struct.unpack('!Q', data)[0]
		return Payload(fiatAmount)

	def __init__(self, fiatAmount):
		self.fiatAmount = fiatAmount


	def encode(self):
		return struct.pack('!Q', self.fiatAmount)



class LightningTransaction:
	def __init__(self, destinationNodeID, paymentHash,
		minCLTVExpiryDelta,
		recipientCryptoAmount, payload
		):

		self.paymentHash = paymentHash
		self.recipientCryptoAmount = recipientCryptoAmount
		self.senderCryptoAmount = int(1.01 * recipientCryptoAmount) #simulated fee
		self.CLTVExpiryDelta = minCLTVExpiryDelta
		self.payload = payload



class Lightning:
	def __init__(self):
		self.lockedTransactions = []


	def getAddress(self):
		return 'dummyLightningAddress'


	def getCurrency(self):
		return 'btc'


	def getDivisor(self):
		# mSatoshi:
		return 100000000000


	def startTransaction(self,
		destinationNodeID, paymentHash,
		recipientCryptoAmount, maxSenderCryptoAmount,
		minCLTVExpiryDelta,
		fiatAmount, fiatCurrency, fiatExchange):

		#TODO: what to do with fiatCurrency, fiatExchange??
		payload = Payload(fiatAmount)

		tx = LightningTransaction(destinationNodeID, paymentHash,
			minCLTVExpiryDelta,
			recipientCryptoAmount, payload
			)

		if tx.senderCryptoAmount > maxSenderCryptoAmount:
			raise Exception('Transaction failed because of too high Lightning fees')

		self.lockedTransactions.append(tx)


	def close(self):
		pass

