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

from bl4p_api import offer



#status
'''
State transitions:

Seller market taker:
initial -> received_BL4P_promise -> locked_lightning_tx ->

Buyer market maker:
locked_lightning_tx ->
'''
STATUS_INITIAL = 0
STATUS_RECEIVED_BL4P_PROMISE = 1
STATUS_LOCKED_LIGHTNING_TX = 2



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
	def __init__(self, localOrderID, counterOffer):
		self.localOrderID = localOrderID
		self.counterOffer = counterOffer
		self.status = STATUS_INITIAL


	def initiate(self, client):
		raise Exception('Not implemented in this class')



class BuyTransaction(Transaction):
	def __init__(self, localOrderID, counterOffer):
		Transaction.__init__(self, localOrderID, counterOffer)
		print('Created buy tx')


	def initiateFromLNTransaction(self, client, lntx):
		print('Initiating buy tx from LN tx')
		#TODO



class SellTransaction(Transaction):
	def __init__(self, localOrderID, counterOffer):
		Transaction.__init__(self, localOrderID, counterOffer)
		print('Created sell tx')


	def initiate(self, client):
		localOffer   = client.storage.getOrder(self.localOrderID)
		counterOffer = self.counterOffer

		#Choose the largest fiat amount accepted by both
		fiatAmountDivisor = client.bl4pAmountDivisor
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
		cryptoAmountDivisor = client.lightning.getDivisor()
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

		#Create transaction on the exchange:
		senderAmount, receiverAmount, paymentHash = \
			client.connection.start(
				fiatAmount,
				sender_timeout_delta_ms,
				locked_timeout_delta_s,
				receiver_pays_fee=True
				)

		assert senderAmount == fiatAmount

		self.minCryptoAmount = minCryptoAmount
		self.maxCryptoAmount = maxCryptoAmount
		self.senderAmount = senderAmount
		self.receiverAmount = receiverAmount
		self.paymentHash = paymentHash
		self.status = STATUS_RECEIVED_BL4P_PROMISE

		#Immediately continue with the next stage:
		self.lockCryptoFunds(client)


	def lockCryptoFunds(self, client):
		localOffer   = client.storage.getOrder(self.localOrderID)
		counterOffer = self.counterOffer

		#Choose the CLTV expiry delta as small as possible
		CLTV_expiry_delta = getMinConditionValue(
			localOffer, counterOffer,
			offer.Condition.CLTV_EXPIRY_DELTA
			)

		#Send out over Lightning:
		assert localOffer.bid.currency == client.lightning.getCurrency()
		assert localOffer.bid.exchange == 'ln'
		client.lightning.startTransaction(
			destinationNodeID=counterOffer.address,
			paymentHash=self.paymentHash,
			recipientCryptoAmount=self.minCryptoAmount,
			maxSenderCryptoAmount=self.maxCryptoAmount,
			minCLTVExpiryDelta=CLTV_expiry_delta,
			fiatAmount=self.receiverAmount,
			fiatCurrency=localOffer.ask.currency,
			fiatExchange=localOffer.ask.exchange
			)

		self.status = STATUS_LOCKED_LIGHTNING_TX

