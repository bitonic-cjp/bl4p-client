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
from typing import Optional

from bl4p_api import offer
import settings
import storage
from storage import StoredObject

'''
Order status
Active -> Completed
'''
STATUS_ACTIVE = 0    #type: int
STATUS_COMPLETED = 1 #type: int



class Order(offer.Offer, StoredObject):
	'''
	An order is executed by the local trading engine.
	It consists of an offer (the data given to external parties),
	with added data that is used locally.

	Attribute:          Source:                                     Unit (typical buy):   Unit (typical sell):

	[Class: Offer]
	ID                  stored
	bid,ask
		max_amount  determined from Order attributes            mCent,mSatoshi        mSatoshi,mCent
		currency    determined from settings (must not change!)
		exchange    determined from settings (must not change!)
	address             determined from LN
	conditions          determined from settings

	[Class: Order]
	limitRate           stored                                      mCent/BTC             mCent/BTC
	amount              stored                                      mCent                 mSatoshi
	status              stored
	perTxMaxAmount      = amount (for now)                          mCent                 mSatoshi
	limitRateInverted   determined by derived class
	remoteOfferID       determined on publishing
	'''

	def __init__(self, storage: storage.Storage, tableName: str, ID: int, limitRateInverted: int, **kwargs) -> None:
		#This initialization is just to inform Mypy about data types.
		#TODO: find a way to make sure storage.Storage respects these types
		self.amount    = None #type: int
		self.limitRate = None #type: int
		self.status    = None #type: int

		offer.Offer.__init__(self, ID=ID, **kwargs)
		StoredObject.__init__(self, storage, tableName, ID)

		self.remoteOfferID = None #type: Optional[int]

		self.perTxMaxAmount = self.amount #type: int #TODO (bug 18)
		self.limitRateInverted = limitRateInverted #type: int
		self.updateOfferMaxAmounts()


	def setAmount(self, value: int) -> None:
		self.update(amount = value) #sets attribute and stores to disk
		self.updateOfferMaxAmounts()


	def updateOfferMaxAmounts(self) -> None:
		'''
		Variable:                                               Unit (typical buy):   Unit (typical sell):
		limitRate                                               mCent/mSatoshi        mSatoshi/mCent
		amount                                                  mCent                 mSatoshi
		'''

		#From integer attributes to Decimal:
		limitRate = decimal.Decimal(self.limitRate) / settings.cryptoDivisor #type: decimal.Decimal
		if self.limitRateInverted:
			limitRate = 1 / limitRate
		amount = decimal.Decimal(self.amount) #type: decimal.Decimal
		perTxMaxAmount = decimal.Decimal(self.perTxMaxAmount) #type: decimal.Decimal

		offerAskAmount = amount / limitRate #type: decimal.Decimal
		offerBidAmount = amount             #type: decimal.Decimal

		if perTxMaxAmount < offerBidAmount:
			offerAskAmount = perTxMaxAmount / limitRate
			offerBidAmount = perTxMaxAmount

		self.bid.max_amount = int(offerBidAmount)
		self.ask.max_amount = int(offerAskAmount) + 1 # + 1 should be insignificant; it's here to make sure we don't round down



class BuyOrder(Order):
	'''
	Buy crypto on LN, sell fiat on BL4P
	'''

	@staticmethod
	def create(
		storage: storage.Storage,
		limitRate: int, # fiat / crypto
		amount   : int, # fiat
		) -> int:
		return StoredObject.createStoredObject(storage, 'buyOrders',
			limitRate = limitRate,
			amount = amount,
			status = STATUS_ACTIVE,
			)


	def __init__(self, storage: storage.Storage, ID: int, LNAddress: str) -> None:
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
			sender_timeout = (100, 10000), #milliseconds

			#We require a maximum lock timeout for outgoing funds
			locked_timeout = (0, 3600*24*14)
			)



class SellOrder(Order):
	'''
	Sell crypto on LN, buy fiat on BL4P
	'''

	@staticmethod
	def create(
		storage: storage.Storage,
		limitRate: int, # fiat / crypto
		amount   : int, # fiat
		) -> int:
		return StoredObject.createStoredObject(storage, 'sellOrders',
			limitRate = limitRate,
			amount = amount,
			status = STATUS_ACTIVE,
			)

	def __init__(self, storage: storage.Storage, ID: int, Bl4PAddress: str) -> None:
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
			sender_timeout = (100, 10000), #milliseconds

			#We require a minimum lock timeout for incoming funds
			#TODO (bug 6): We MUST NEVER make Lightning routes with
			#a longer time than the lock timeout
			locked_timeout = (3600*24, offer.CONDITION_NO_MAX),
			)

