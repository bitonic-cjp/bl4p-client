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
from storage import StoredObject



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



class Order(offer.Offer, StoredObject):
	'''
	An order is executed by the local trading engine.
	It consists of an offer (the data given to external parties),
	with added data that is used locally.

	Attributes:

	Offer:
	ID                  stored
	bid,ask
		max_amount  determined from Order attributes
		currency    determined from settings (must not change!)
		exchange    determined from settings (must not change!)
	address             determined from LN
	conditions          determined from settings

	Order:
	limitRate           stored
	amount              stored (was: totalBidAmount)

	perTxMaxAmount      = totalBidAmount
	perTxMaxAmountSide  = BID
	limitRateInverted   determined by derived class
	remoteOfferID       determined on publishing
	status              determined from stored transactions
	'''

	def __init__(self, storage, tableName, ID, limitRateInverted, **kwargs):
		offer.Offer.__init__(self, ID=ID, **kwargs)
		StoredObject.__init__(self, storage, tableName, ID)

		self.remoteOfferID = None
		self.status = STATUS_IDLE #TODO: derive from database

		self.perTxMaxAmount = self.amount #TODO
		self.perTxMaxAmountSide = BID
		self.limitRateInverted = limitRateInverted
		self.updateOfferMaxAmounts()


	def setAmount(self, value):
		self.amount = value
		self.updateOfferMaxAmounts()


	def updateOfferMaxAmounts(self):
		#From integer attributes to Decimal:
		limitRate = decimal.Decimal(self.limitRate) / settings.cryptoDivisor
		if self.limitRateInverted:
			limitRate = 1 / limitRate
		amount = decimal.Decimal(self.amount)
		perTxMaxAmount = decimal.Decimal(self.perTxMaxAmount)

		offerAskAmount = amount / limitRate
		offerBidAmount = amount

		if self.perTxMaxAmountSide == BID and perTxMaxAmount < offerBidAmount:
			offerAskAmount = perTxMaxAmount / limitRate
			offerBidAmount = perTxMaxAmount

		if self.perTxMaxAmountSide == ASK and perTxMaxAmount < offerAskAmount:
			offerAskAmount = perTxMaxAmount
			offerBidAmount = perTxMaxAmount * limitRate

		self.bid.max_amount = int(offerBidAmount)
		self.ask.max_amount = int(offerAskAmount) + 1 # + 1 should be insignificant; it's here to make sure we don't round down



class BuyOrder(Order):
	'''
	Buy crypto on LN, sell fiat on BL4P
	'''

	@staticmethod
	def create(
		storage,
		limitRate, # fiat / crypto
		amount,    # fiat
		):
		return StoredObject.create(storage, 'buyOrders',
			limitRate = limitRate,
			amount = amount,
			)


	def __init__(self, storage, ID, LNAddress):
		Order.__init__(self,
			storage, 'buyOrders', ID,
			limitRateInverted=False,

			address=LNAddress,

			bid=offer.Asset(
				max_amount=0, max_amount_divisor=settings.fiatDivisor, currency=settings.fiatName, exchange='bl3p.eu'
				),
			ask=offer.Asset(
				max_amount=0, max_amount_divisor=settings.cryptoDivisor, currency=settings.cryptoName, exchange='ln'
				),

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

	@staticmethod
	def create(
		storage,
		limitRate, # fiat / crypto
		amount,    # fiat
		):
		return StoredObject.create(storage, 'sellOrders',
			limitRate = limitRate,
			amount = amount,
			)

	def __init__(self, storage, ID, Bl4PAddress):
		Order.__init__(self,
			storage, 'sellOrders', ID,
			limitRateInverted=True,

			address=Bl4PAddress,

			bid=offer.Asset(
				max_amount=0, max_amount_divisor=settings.cryptoDivisor, currency=settings.cryptoName, exchange='ln'
				),
			ask=offer.Asset(
				max_amount=0, max_amount_divisor=settings.fiatDivisor, currency=settings.fiatName, exchange='bl3p.eu'
				),

			#We require a maximum CLTV time for outgoing funds
			cltv_expiry_delta = (0, 144),

			#We require a maximum sender timeout for incoming funds
			sender_timeout = (10, 10000), #milliseconds

			#We require a minimum lock timeout for incoming funds
			#TODO: We MUST NEVER make Lightning routes with a longer time than the lock timeout
			locked_timeout = (3600*24, offer.CONDITION_NO_MAX),
			)

