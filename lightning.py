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
import time



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



class LightningTransaction:
	def __init__(self, destinationNodeID, paymentHash,
		minCLTVExpiryDelta,
		recipientCryptoAmount, payload
		):

		self.destination = destinationNodeID
		self.paymentHash = paymentHash
		self.recipientCryptoAmount = recipientCryptoAmount
		self.senderCryptoAmount = int(1.01 * recipientCryptoAmount) #simulated fee
		self.CLTVExpiryDelta = minCLTVExpiryDelta
		self.payload = payload



class Lightning:
	def __init__(self):
		self.sentTransactions = []
		self.receivedTransactions = []


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
		fiatAmount,
		offerID,
		):

		payload = Payload(fiatAmount, offerID)

		tx = LightningTransaction(destinationNodeID, paymentHash,
			minCLTVExpiryDelta,
			recipientCryptoAmount, payload
			)

		if tx.senderCryptoAmount > maxSenderCryptoAmount:
			raise Exception('Transaction failed because of too high Lightning fees')

		self.sentTransactions.append(tx)


	def waitForIncomingTransactions(self, timeout):
		#TODO: also return events for cancelations of outgoing transactions
		while self.sentTransactions:
			tx = self.sentTransactions.pop(0)

			if tx.destination != self.getAddress():
				continue #it's not ours

			self.receivedTransactions.append(tx)
			return tx

		time.sleep(timeout)
		return None


	def close(self):
		pass

