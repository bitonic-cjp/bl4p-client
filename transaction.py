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

import hashlib

from bl4p_api import offer
from log import log
import settings



sha256 = lambda preimage: hashlib.sha256(preimage).digest()



#status
'''
State transitions:

Seller market taker:
initial -> locked -> received_preimage -> finished

Buyer market maker:
locked -> received_preimage -> finished
'''
STATUS_INITIAL = 0
STATUS_LOCKED = 1
STATUS_RECEIVED_PREIMAGE = 2
STATUS_FINISHED = 3


def getMinConditionValue(offer1, offer2, condition):
	return max(
		offer1.getConditionMin(condition),
		offer2.getConditionMin(condition)
		)


def getMaxConditionValue(offer1, offer2, condition):
	return min(
		offer1.getConditionMax(condition),
		offer2.getConditionMax(condition)
		)



class Transaction:
	def __init__(self, localOrderID):
		self.localOrderID = localOrderID
		self.status = STATUS_INITIAL
		self.paymentHash = None
		self.paymentPreimage = None



class BuyTransaction(Transaction):
	def __init__(self, localOrderID):
		Transaction.__init__(self, localOrderID)
		log('Created buy tx')


	def initiateFromLNIncoming(self, localOffer, message):
		#TODO: check if lntx conforms to our order
		#TODO: check if remaining order size is sufficient

		self.cryptoAmount = message.cryptoAmount
		self.fiatAmount = message.fiatAmount
		self.paymentHash = message.paymentHash
		self.status = STATUS_LOCKED
		#TODO:


	#TODO: unlock the following functionality:
	'''
	def lockFiatFunds(self, client):
		paymentPreimage = client.connection.send(
			self.fiatAmount, self.paymentHash)
		#TODO: handle failure of the above

		assert sha256(paymentPreimage) == self.paymentHash

		self.paymentPreimage = paymentPreimage
		self.status = STATUS_SENT_BL4P_FUNDS

		log('We got the preimage from BL4P')
		self.receiveCryptoTransaction(client)


	def receiveCryptoTransaction(self, client):
		client.lightning.finishIncomingTransaction(
			self.paymentHash, self.paymentPreimage)

		self.status = STATUS_FINISHED
	'''



class SellTransaction(Transaction):
	def __init__(self, localOrderID):
		Transaction.__init__(self, localOrderID)
		log('Created sell tx')


	def initiateFromCounterOffer(self, localOffer, counterOffer):
		#Choose the largest fiat amount accepted by both
		fiatAmountDivisor = settings.fiatDivisor
		fiatAmount = min(
			fiatAmountDivisor * localOffer.ask.max_amount // localOffer.ask.max_amount_divisor,
			fiatAmountDivisor * counterOffer.bid.max_amount // counterOffer.bid.max_amount_divisor
			)
		assert fiatAmount > 0

		#Minimum: this is what the other wants
		#btc = eur * (btc / eur)
		#    = eur * (ask / bid)
		#    = eur * (ask / ask_divisor) / (bid / bid_divisor)
		#    = (eur * ask * bid_divisor) / (bid * ask_divisor)
		#Implementation note:
		#The correctness of this code might depend on Python's unlimited size integers.
		cryptoAmountDivisor = settings.cryptoDivisor
		minCryptoAmount = \
			(cryptoAmountDivisor * fiatAmount        * counterOffer.ask.max_amount         * counterOffer.bid.max_amount_divisor) // \
			(                      fiatAmountDivisor * counterOffer.ask.max_amount_divisor * counterOffer.bid.max_amount)
		#Maximum: this is what we are prepared to pay
		maxCryptoAmount = \
			(cryptoAmountDivisor * fiatAmount        * localOffer.bid.max_amount         * localOffer.ask.max_amount_divisor) // \
			(                      fiatAmountDivisor * localOffer.bid.max_amount_divisor * localOffer.ask.max_amount)
		assert minCryptoAmount >= 0
		assert maxCryptoAmount >= minCryptoAmount

		#Choose the sender timeout limit as small as possible
		sender_timeout_delta_ms = getMinConditionValue(
			localOffer, counterOffer,
			offer.Condition.SENDER_TIMEOUT
			)

		#Choose the locked timeout limit as large as possible
		locked_timeout_delta_s = getMaxConditionValue(
			localOffer, counterOffer,
			offer.Condition.LOCKED_TIMEOUT
			)

		#Choose the CLTV expiry delta as small as possible
		CLTV_expiry_delta = getMinConditionValue(
			localOffer, counterOffer,
			offer.Condition.CLTV_EXPIRY_DELTA
			)

		self.counterOffer = counterOffer
		self.fiatAmount = fiatAmount
		self.minCryptoAmount = minCryptoAmount
		self.maxCryptoAmount = maxCryptoAmount
		self.sender_timeout_delta_ms = sender_timeout_delta_ms
		self.locked_timeout_delta_s = locked_timeout_delta_s
		self.CLTV_expiry_delta = CLTV_expiry_delta


	#TODO: unlock the following functionality:
	'''
	def receiveFiatFunds(self, client, paymentPreimage):
		self.paymentPreimage = paymentPreimage
		self.status = STATUS_RECEIVED_PREIMAGE

		client.connection.receive(paymentPreimage)

		self.status = STATUS_FINISHED

		log('Transaction is finished')
	'''

