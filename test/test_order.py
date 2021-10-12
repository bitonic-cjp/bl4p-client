#    Copyright (C) 2019-2021 by Bitonic B.V.
#
#    This file is part of the BL4P Client.
#
#    The BL4P Client is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    The BL4P Client is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with the BL4P Client. If not, see <http://www.gnu.org/licenses/>.

import sys
import unittest
from unittest.mock import patch, Mock

sys.path.append('..')

from bl4p_api import offer
import order



class TestOrder(unittest.TestCase):
	def setUp(self):
		self.storage = Mock()
		self.cursor = Mock()
		self.cursor.description = [['ID'], ['amount'], ['limitRate']]
		self.cursor.fetchone = Mock(return_value = [42, 6000000, 200000]) #60 eur @ 2 eur/btc
		self.storage.execute = Mock(return_value=self.cursor)
		order.StoredObject.createStoredObject = Mock(return_value=43)

		self.order = order.Order(
			self.storage, 'foo', 42, False,

			address='bar',
			bid=offer.Asset(max_amount=0, max_amount_divisor=100000000000, currency='btc', exchange='ln'),
			ask=offer.Asset(max_amount=0, max_amount_divisor=100000      , currency='eur', exchange='bl3p.eu'),
			)


	def test_constructor(self):
		self.assertEqual(self.order.ID, 42)
		self.assertEqual(self.order.bid.max_amount, 6000000) #60 eur
		self.assertEqual(self.order.bid.currency, 'btc')
		self.assertEqual(self.order.bid.exchange, 'ln')
		self.assertEqual(self.order.ask.max_amount, 3000000000001) #30 btc
		self.assertEqual(self.order.ask.currency, 'eur')
		self.assertEqual(self.order.ask.exchange, 'bl3p.eu')
		self.assertEqual(self.order.address, 'bar')

		self.assertEqual(self.order.limitRate, 200000) #2 eur/btc
		self.assertEqual(self.order.amount, 6000000) #60 eur
		self.assertEqual(self.order.perTxMaxAmount, 6000000) #60 eur
		self.assertEqual(self.order.limitRateInverted, False)
		self.assertEqual(self.order.remoteOfferID, None)

		self.storage.execute.assert_called_once_with('SELECT * from foo WHERE `ID` = ?', (42,))


	def test_setAmount(self):
		cursor = Mock()
		self.storage.execute = Mock(return_value=cursor)

		self.order.setAmount(3000000) #30 eur

		self.storage.execute.assert_called_once_with('UPDATE foo SET (`amount`) = (?) WHERE `ID` = ?', [3000000, 42])
		self.assertEqual(self.order.amount, 3000000) #30 eur
		self.assertEqual(self.order.bid.max_amount, 3000000) #30 eur
		self.assertEqual(self.order.ask.max_amount, 1500000000001) #15 btc


	def test_updateOfferMaxAmounts(self):
		#Unlimited, non-inverted rate
		self.order.amount             = 6000000   # 60 eur
		self.order.limitRate          = 200000000 # 2000 eur/btc
		self.order.perTxMaxAmount     = 6000000   # 60 eur
		self.order.limitRateInverted  = False
		self.order.updateOfferMaxAmounts()
		self.assertEqual(self.order.bid.max_amount, 6000000) #60 eur
		self.assertEqual(self.order.ask.max_amount, 3000000001) #0.03 btc

		#Unlimited, inverted rate
		self.order.amount             = 3000000000 # 0.03 btc
		self.order.limitRate          = 200000000  # 2000 eur/btc
		self.order.perTxMaxAmount     = 3000000000 # 0.03 btc
		self.order.limitRateInverted  = True
		self.order.updateOfferMaxAmounts()
		self.assertEqual(self.order.bid.max_amount, 3000000000) # 0.03 btc
		self.assertEqual(self.order.ask.max_amount, 6000001)    # 60 eur

		#Limited, non-inverted rate
		self.order.amount             = 6000000   # 60 eur
		self.order.limitRate          = 200000000 # 2000 eur/btc
		self.order.perTxMaxAmount     = 1000000   # 10 eur
		self.order.limitRateInverted  = False
		self.order.updateOfferMaxAmounts()
		self.assertEqual(self.order.bid.max_amount, 1000000) #10 eur
		self.assertEqual(self.order.ask.max_amount, 500000001) #0.005 btc


	def test_BuyOrder(self):
		self.assertEqual(order.BuyOrder.create('foo', 'bar', 'baz'), 43)
		order.StoredObject.createStoredObject.assert_called_once_with('foo', 'buyOrders', limitRate='bar', amount='baz', status=0)

		buy = order.BuyOrder(self.storage, 42, 'foo')
		self.assertEqual(buy.ID, 42)
		self.assertEqual(buy._tableName, 'buyOrders')
		self.assertEqual(buy.limitRateInverted, False)
		self.assertEqual(buy.address, 'foo')
		self.assertEqual(buy.bid.max_amount_divisor, 100000)
		self.assertEqual(buy.bid.currency, 'eur')
		self.assertEqual(buy.bid.exchange, 'bl3p.eu')
		self.assertEqual(buy.ask.max_amount_divisor, 100000000000)
		self.assertEqual(buy.ask.currency, 'btc')
		self.assertEqual(buy.ask.exchange, 'ln')

		self.assertEqual(buy.getConditionMin(offer.Condition.CLTV_EXPIRY_DELTA), 12)
		self.assertEqual(buy.getConditionMax(offer.Condition.CLTV_EXPIRY_DELTA), offer.CONDITION_NO_MAX)
		self.assertEqual(buy.getConditionMin(offer.Condition.SENDER_TIMEOUT), 10000)
		self.assertEqual(buy.getConditionMax(offer.Condition.SENDER_TIMEOUT), 30000)
		self.assertEqual(buy.getConditionMin(offer.Condition.LOCKED_TIMEOUT), 0)
		self.assertEqual(buy.getConditionMax(offer.Condition.LOCKED_TIMEOUT), 3600*24*14)


	def test_SellOrder(self):
		self.assertEqual(order.SellOrder.create('foo', 'bar', 'baz'), 43)
		order.StoredObject.createStoredObject.assert_called_once_with('foo', 'sellOrders', limitRate='bar', amount='baz', status=0)

		sell = order.SellOrder(self.storage, 42, 'foo')
		self.assertEqual(sell.ID, 42)
		self.assertEqual(sell._tableName, 'sellOrders')
		self.assertEqual(sell.limitRateInverted, True)
		self.assertEqual(sell.address, 'foo')
		self.assertEqual(sell.bid.max_amount_divisor, 100000000000)
		self.assertEqual(sell.bid.currency, 'btc')
		self.assertEqual(sell.bid.exchange, 'ln')
		self.assertEqual(sell.ask.max_amount_divisor, 100000)
		self.assertEqual(sell.ask.currency, 'eur')
		self.assertEqual(sell.ask.exchange, 'bl3p.eu')

		self.assertEqual(sell.getConditionMin(offer.Condition.CLTV_EXPIRY_DELTA), 0)
		self.assertEqual(sell.getConditionMax(offer.Condition.CLTV_EXPIRY_DELTA), 144)
		self.assertEqual(sell.getConditionMin(offer.Condition.SENDER_TIMEOUT), 2000)
		self.assertEqual(sell.getConditionMax(offer.Condition.SENDER_TIMEOUT), 10000)
		self.assertEqual(sell.getConditionMin(offer.Condition.LOCKED_TIMEOUT), 3600*24)
		self.assertEqual(sell.getConditionMax(offer.Condition.LOCKED_TIMEOUT), offer.CONDITION_NO_MAX)



if __name__ == '__main__':
	unittest.main(verbosity=2)

