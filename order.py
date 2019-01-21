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


#Side constants
BID = True
ASK = False

#Order status constants
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
			limitRate, #bid / ask, so EUR/BTC for buy, BTC/EUR for sell
			totalBidAmount, #bid amount, so EUR for buy, BTC for sell
			settings,
			**kwargs):

		offer.Offer.__init__(self, **kwargs)
		self.limitRate = limitRate
		self.totalBidAmount = totalBidAmount
		self.perTxMaxAmount = totalBidAmount #TODO
		self.perTxMaxAmountSide = BID
		self.status = STATUS_IDLE

		self.settings = settings
		self.updateOfferMaxAmounts()


	def getCondition(self, condition, index):
		return self.conditions[condition][index]


	def setCondition(self, condition, index, value):
		old = self.conditions[condition]
		self.conditions[condition] = \
			(value, old[1]) \
			if index == 0 else \
			(old[0], value)


	def getTotalBidAmount(self):
		return '%s %s' % (
			str(decimal.Decimal(self.totalBidAmount) / self.bid.max_amount_divisor),
			self.bid.currency
			)


	def setTotalBidAmount(self, value):
		self.totalBidAmount = decimal.Decimal(value) * self.bid.max_amount_divisor
		self.updateOfferMaxAmounts()


	def getPerTxMaxAmount(self):
		asset = self.bid if self.perTxMaxAmountSide == BID else self.ask
		return '%s %s' % (
			str(decimal.Decimal(self.perTxMaxAmount) / asset.max_amount_divisor),
			asset.currency
			)


	def setPerTxMaxAmount(self, value):
		self.perTxMaxAmount, self.perTxMaxAmountSide = value
		self.updateOfferMaxAmounts()


	def listSettings(self):
		ret = {}
		for k, v in self.settings.items():
			getter = v[0]
			extraArgs = v[2:]
			ret[k] = getter(*extraArgs)
		return ret


	def setSetting(self, name, value):
		definition = self.settings[name]
		setter = definition[1]
		extraArgs = definition[2:]
		setter(*extraArgs, value)


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
	Buy BTC on LN, sell EUR on BL4P
	'''

	def __init__(self,
		limitRate,     # EUR / BTC
		totalBidAmount # EUR
		):

		Order.__init__(self,
			limitRate=limitRate,
			totalBidAmount=totalBidAmount,
			settings=\
			{
			'limitRate'       : (self.getLimitRate, self.setLimitRate),
			'totalBidAmount'  : (self.getTotalBidAmount, self.setTotalBidAmount),
			'perTxMaxAmount'  : (self.getPerTxMaxAmount, self.setPerTxMaxAmount),
			'minCLTV'         : (self.getCondition, self.setCondition, offer.Condition.CLTV_EXPIRY_DELTA, 0),
			'maxLockedTimeout': (self.getCondition, self.setCondition, offer.Condition.LOCKED_TIMEOUT, 1),
			},

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


	def getLimitRate(self):
		return '%s %s/%s' % (
			str(decimal.Decimal(self.limitRate) * \
				self.ask.max_amount_divisor /
				self.bid.max_amount_divisor),
			self.bid.currency, self.ask.currency
			)


	def setLimitRate(self, value):
		self.limitRate = decimal.Decimal(value) * \
			self.bid.max_amount_divisor / self.ask.max_amount_divisor
		self.updateOfferMaxAmounts()



class SellOrder(Order):
	'''
	Sell BTC on LN, buy EUR on BL4P
	'''

	def __init__(self,
		limitRate,     # EUR / BTC
		totalBidAmount # BTC
		):

		Order.__init__(self,
			limitRate=1/limitRate,
			totalBidAmount=totalBidAmount,
			settings=\
			{
			'limitRate'       : (self.getLimitRate, self.setLimitRate),
			'totalBidAmount'  : (self.getTotalBidAmount, self.setTotalBidAmount),
			'perTxMaxAmount'  : (self.getPerTxMaxAmount, self.setPerTxMaxAmount),
			'maxCLTV'         : (self.getCondition, self.setCondition, offer.Condition.CLTV_EXPIRY_DELTA, 1),
			'minLockedTimeout': (self.getCondition, self.setCondition, offer.Condition.LOCKED_TIMEOUT, 0),
			},

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


	def getLimitRate(self):
		return '%s %s/%s' % (
			str(1 / decimal.Decimal(self.limitRate) * \
				self.bid.max_amount_divisor /
				self.ask.max_amount_divisor),
			self.ask.currency, self.bid.currency
			)


	def setLimitRate(self, value):
		self.limitRate = (1 / decimal.Decimal(value)) * \
			self.bid.max_amount_divisor / self.ask.max_amount_divisor
		self.updateOfferMaxAmounts()

