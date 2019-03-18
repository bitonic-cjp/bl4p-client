#    Copyright (C) 2018-2019 by Bitonic B.V.
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

import decimal

from bl4p_api import offer
import settings



#Side constants
BID = True
ASK = False

#Order status constants
'''
State transitions:

idle -> trading
trading -> completed
trading -> idle
'''
STATUS_IDLE = 0
STATUS_TRADING = 1
STATUS_COMPLETED = 2



class Order(offer.Offer):
	'''
	An order is executed by the local trading engine.
	It consists of an offer (the data given to external parties),
	with added data that is used locally.
	'''

	def __init__(self,
			limitRate, #bid / ask, so fiat/crypto for buy, crypto/fiat for sell
			totalBidAmount, #bid amount, so fiat for buy, crypto for sell
			**kwargs):

		offer.Offer.__init__(self, **kwargs)
		self.limitRate = limitRate
		self.totalBidAmount = totalBidAmount
		self.perTxMaxAmount = totalBidAmount #TODO
		self.perTxMaxAmountSide = BID
		self.remoteOfferID = None
		self.status = STATUS_IDLE

		self.updateOfferMaxAmounts()


	def setTotalBidAmount(self, value):
		self.totalBidAmount = value
		self.updateOfferMaxAmounts()


	def updateOfferMaxAmounts(self):
		offerAskAmount = self.totalBidAmount / self.limitRate
		offerBidAmount = self.totalBidAmount

		if self.perTxMaxAmountSide == BID and self.perTxMaxAmount < offerBidAmount:
			offerAskAmount = self.perTxMaxAmount / self.limitRate
			offerBidAmount = self.perTxMaxAmount

		if self.perTxMaxAmountSide == ASK and self.perTxMaxAmount < offerAskAmount:
			offerAskAmount = self.perTxMaxAmount
			offerBidAmount = self.perTxMaxAmount * self.limitRate

		self.bid.max_amount = int(offerBidAmount)
		self.ask.max_amount = int(offerAskAmount) + 1 # + 1 should be insignificant; it's here to make sure we don't round down



class BuyOrder(Order):
	'''
	Buy crypto on LN, sell fiat on BL4P
	'''

	def __init__(self,
		LNAddress,
		limitRate,     # fiat / crypto
		totalBidAmount # fiat
		):

		Order.__init__(self,
			limitRate=limitRate,
			totalBidAmount=totalBidAmount,

			bid=offer.Asset(
				max_amount=0, max_amount_divisor=settings.fiatDivisor, currency=settings.fiatName, exchange='bl3p.eu'
				),
			ask=offer.Asset(
				max_amount=0, max_amount_divisor=settings.cryptoDivisor, currency=settings.cryptoName, exchange='ln'
				),
			address=LNAddress,
			ID=None, #To be filled in later

			#We require a minimum CLTV time for incoming funds
			cltv_expiry_delta = (12, offer.CONDITION_NO_MAX),

			#We require a maximum sender timeout for outgoming funds
			sender_timeout = (10, 10000), #milliseconds

			#We require a maximum lock timeout for outgoing funds
			locked_timeout = (0, 3600*24*14)
			)




class SellOrder(Order):
	'''
	Sell crypto on LN, buy fiat on BL4P
	'''

	def __init__(self,
		Bl4PAddress,
		limitRate,     # fiat / crypto
		totalBidAmount # crypto
		):

		Order.__init__(self,
			limitRate=1/limitRate,
			totalBidAmount=totalBidAmount,

			bid=offer.Asset(
				max_amount=0, max_amount_divisor=settings.cryptoDivisor, currency=settings.cryptoName, exchange='ln'
				),
			ask=offer.Asset(
				max_amount=0, max_amount_divisor=settings.fiatDivisor, currency=settings.fiatName, exchange='bl3p.eu'
				),
			address=Bl4PAddress,
			ID=None, #To be filled in later

			#We require a maximum CLTV time for outgoing funds
			cltv_expiry_delta = (0, 144),

			#We require a maximum sender timeout for incoming funds
			sender_timeout = (10, 10000), #milliseconds

			#We require a minimum lock timeout for incoming funds
			#TODO: We MUST NEVER make Lightning routes with a longer time than the lock timeout
			locked_timeout = (3600*24, offer.CONDITION_NO_MAX),
			)

