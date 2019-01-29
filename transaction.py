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
STATUS_INITIAL = 0
STATUS_RECEIVED_BL4P_PROMISE = 1



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



class SellTransaction(Transaction):
	def __init__(self, localOrderID, counterOffer):
		Transaction.__init__(self, localOrderID, counterOffer)
		print('Created sell tx')


	def initiate(self, client):
		localOffer   = client.storage.getOrder(self.localOrderID)
		counterOffer = self.counterOffer

		#Choose the largest amount accepted by both
		amountDivisor = client.bl4pAmountDivisor
		amount = min(
			amountDivisor * localOffer.ask.max_amount // localOffer.ask.max_amount_divisor,
			amountDivisor * counterOffer.bid.max_amount // counterOffer.bid.max_amount_divisor
			)

		#Choose the sender timeout limit as small as possible
		#TODO: make sure it works even if conditions are not specified
		sender_timeout_delta_ms = max(
			localOffer.conditions[offer.Condition.SENDER_TIMEOUT][0],
			counterOffer.conditions[offer.Condition.SENDER_TIMEOUT][0]
			)

		#Choose the locked timeout limit as large as possible
		#TODO: make sure it works even if conditions are not specified
		locked_timeout_delta_s = min(
			localOffer.conditions[offer.Condition.LOCKED_TIMEOUT][1],
			counterOffer.conditions[offer.Condition.LOCKED_TIMEOUT][1]
			)

		senderAmount, receiverAmount, paymentHash = \
			client.connection.start(
				amount,
				sender_timeout_delta_ms,
				locked_timeout_delta_s,
				receiver_pays_fee=True
				)

		if senderAmount != amount:
			raise Exception('Got incorrect sender amount back from BL4P')

		self.senderAmount = senderAmount
		self.receiverAmount = receiverAmount
		self.paymentHash = paymentHash
		self.status = STATUS_RECEIVED_BL4P_PROMISE

		#TODO: send out over Lightning

