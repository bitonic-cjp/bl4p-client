#    Copyright (C) 2018 by Bitonic B.V.
#
#    This file is part of the BL4P API.
#
#    The BL4P API is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    The BL4P API is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with the BL4P API. If not, see <http://www.gnu.org/licenses/>.

from . import offer_pb2



def Asset(max_amount, max_amount_divisor, currency, exchange):
	ret = offer_pb2.Offer.Asset()
	ret.max_amount = max_amount
	ret.max_amount_divisor = max_amount_divisor
	ret.currency = currency
	ret.exchange = exchange
	return ret



class Offer:
	@staticmethod
	def fromPB2(pb2):
		ret = Offer(pb2.bid, pb2.ask, pb2.address)

		for condition in pb2.conditions:
			ret.conditions[condition.key] = \
				(condition.min_value, condition.max_value)

		return ret


	def __init__(self,
			bid, ask,
			address,
			cltv_expiry_delta = None, #None or (min, max)
			locked_timeout = None,    #None or (min, max)
			):
		self.bid = bid
		self.ask = ask
		self.address = address
		self.conditions = {}
		Condition = offer_pb2.Offer.Condition
		if cltv_expiry_delta is not None:
			self.conditions[Condition.CLTV_EXPIRY_DELTA] = cltv_expiry_delta
		if locked_timeout is not None:
			self.conditions[Condition.LOCKED_TIMEOUT] = locked_timeout


	def __eq__(self, other):
		return self.__dict__ == other.__dict__


	def toPB2(self):
		ret = offer_pb2.Offer()
		ret.bid.CopyFrom(self.bid)
		ret.ask.CopyFrom(self.ask)
		ret.address = self.address

		Condition = offer_pb2.Offer.Condition
		for key, minmax in self.conditions.items():
			condition = ret.conditions.add()
			condition.key = key
			condition.min_value, condition.max_value = minmax
		return ret


	def matches(self, other):
		#Must be matching currency and exchange:
		if \
			self.bid.currency != other.ask.currency or \
			self.bid.exchange != other.ask.exchange or \
			self.ask.currency != other.bid.currency or \
			self.ask.exchange != other.bid.exchange:
				return False

		#All condition ranges must overlap
		commonKeys = set(self.conditions.keys()) & set(other.conditions.keys())
		testOverlap = lambda r1, r2: r1[0] <= r2[1] and r2[0] <= r1[1]
		overlaps = \
		(
		testOverlap(self.conditions[key], other.conditions[key])
		for key in commonKeys
		)
		if False in overlaps:
			return False

		#Must have compatible limit rates
		#One should bid at least as much as the other asks.
		#    bid1 / ask1 >= ask2 / bid2
		#    bid1 * bid2 >= ask1 * ask2
		#    (bid1 / bid1_div) * (bid2 / bid2_div) >= (ask1 / ask1_div) * (ask2 / ask2_div)
		#    bid1 * bid2 * ask1_div * ask2_div >= ask1 * ask2 * bid1_div * bid2_div

		#Implementation note: multiplying all these numbers together may give quite large results.
		#The correctness may well depend on Python's unlimited-size integers.
		return \
			self.bid.max_amount * other.bid.max_amount * \
			self.ask.max_amount_divisor * other.ask.max_amount_divisor \
				>= \
			self.ask.max_amount * other.ask.max_amount * \
			self.bid.max_amount_divisor * other.bid.max_amount_divisor

