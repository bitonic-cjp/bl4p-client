#    Copyright (C) 2018 by Bitonic B.V.
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

import copy
from fractions import Fraction

from bl4p_api import offer



#Some common units:
BTC = 100000000000 #in mSatoshi
mBTC = BTC // 1000

EUR = 100000       #in mCent

#Some settings (TODO: make configurable):
lnAddress = 'dummyLightningAddress'
bl4pAddress = 'dummyBL4PAddress'


BID = True
ASK = False



class Order(offer.Offer):
	'''
	An order is executed by the local trading engine.
	It consists of an offer (the data given to external parties),
	with added data that is used locally.
	'''

	def __init__(self,
			limitRate, #bid / ask, so EUR/BTC for buy, BTC/EUR for sell
			**kwargs):

		offer.Offer.__init__(self, **kwargs)
		self.limitRate = limitRate
		self.totalAmount = 0
		self.totalAmountSide = BID
		self.perTxMaxAmount = 0
		self.perTxMaxAmountSide = BID

		self.updateOfferMaxAmounts()


	def updateOfferMaxAmounts(self):
		if self.totalAmountSide == BID:
			offerAskAmount = self.totalAmount / self.limitRate
			offerBidAmount = self.totalAmount
		else:
			offerAskAmount = self.totalAmount
			offerBidAmount = self.totalAmount * self.limitRate

		if self.perTxMaxAmountSide == BID and self.perTxMaxAmount < offerBidAmount:
			offerAskAmount = self.perTxMaxAmount / self.limitRate
			offerBidAmount = self.perTxMaxAmount

		if self.perTxMaxAmountSide == ASK and self.perTxMaxAmount < offerAskAmount:
			offerAskAmount = self.perTxMaxAmount
			offerBidAmount = self.perTxMaxAmount * self.limitRate

		self.bid.max_amount = int(offerBidAmount)
		self.ask.max_amount = int(offerAskAmount)



class BuyOrder(Order):
	'''
	Buy BTC on LN, sell EUR on BL4P
	'''

	def __init__(self, limitRate):
		Order.__init__(self,
			limitRate=limitRate,

			bid=offer.Asset(
				max_amount=0, max_amount_divisor=EUR, currency='eur', exchange='bl3p.eu'
				),
			ask=offer.Asset(
				max_amount=0, max_amount_divisor=BTC, currency='btc', exchange='ln'
				),
			address=lnAddress,

			#We require a minimum CLTV time for incoming funds
			cltv_expiry_delta = (12, offer.CONDITION_NO_MAX),

			#We require a maximum lock timeout for outgoing funds
			locked_timeout = (0, 3600*24*14)
			)



class SellOrder(Order):
	'''
	Sell BTC on LN, buy EUR on BL4P
	'''

	def __init__(self, limitRate):
		Order.__init__(self,
			limitRate=1/limitRate,

			bid=offer.Asset(
				max_amount=0, max_amount_divisor=BTC, currency='btc', exchange='ln'
				),
			ask=offer.Asset(
				max_amount=0, max_amount_divisor=EUR, currency='eur', exchange='bl3p.eu'
				),
			address=bl4pAddress,

			#We require a maximum CLTV time for outgoing funds
			cltv_expiry_delta = (0, 144),

			#We require a minimum lock timeout for incoming funds
			#TODO: We MUST NEVER make Lightning routes with a longer time than the lock timeout
			locked_timeout = (3600*24, offer.CONDITION_NO_MAX),
			)

