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

import fractions
from functools import reduce
import operator



EUR = \
{
'eur': 10000,
}
BTC = \
{
'msatoshi': 1,
'satoshi' : 1000,
'ubtc'    : 100000,
'mbtc'    : 100000000,
'btc'     : 100000000000,
}
TIME = \
{
'second': 1,
'minute': 60,
'hour'  : 3600,
'day'   : 3600*24,
}

quantities = {}
quantities.update({unit: EUR for unit in EUR.keys()})
quantities.update({unit: BTC for unit in BTC.keys()})
quantities.update({unit: TIME for unit in TIME.keys()})

multipliers = {unit: quantities[unit][unit] for unit in quantities.keys()}



class Unit:
	@staticmethod
	def fromStr(s):
		s = s.split('/')
		if len(s) > 1:
			numerator, denominator = s
		else:
			numerator, denominator = s[0], ''
		numerator   = numerator.split('*')
		denominator = denominator.split('*')
		numerator   = map(lambda s: s.strip(), numerator)
		denominator = map(lambda s: s.strip(), denominator)
		numerator   = list(filter(lambda s: s, numerator))
		denominator = list(filter(lambda s: s, denominator))
		return Unit(numerator, denominator)


	def __init__(self, numerator=[], denominator=[]):
		'''
		Usage:
		Unit((unit, ...), (unit, ...))
		'''
		self.numerator = numerator
		self.denominator = denominator


	def __str__(self):
		numerator   = '*'.join([q for q in self.numerator  ]) if self.numerator   else '1'
		denominator = '*'.join([q for q in self.denominator]) if self.denominator else None

		if denominator:
			return numerator + ' / ' + denominator
		return numerator


	def getMultiplier(self):
		numerator   = [multipliers[q] for q in self.numerator]
		denominator = [multipliers[q] for q in self.denominator]
		numerator   = reduce(operator.mul, numerator  , 1)
		denominator = reduce(operator.mul, denominator, 1)
		return fractions.Fraction(numerator, denominator)


	def getQuantity(self):
		numerator   = [id(quantities[q]) for q in self.numerator]
		denominator = [id(quantities[q]) for q in self.denominator]
		numerator.sort()
		denominator.sort()
		#TODO: simplify by eliminating elements that exist in both
		return numerator, denominator



class UnitValue:
	@staticmethod
	def fromStr(s, numericType):
		lastDigit = None
		for i in range(len(s)):
			if s[i].isdigit():
				lastDigit = i
		value = numericType(s[:lastDigit+1])
		unit = Unit.fromStr(s[lastDigit+1:])
		return UnitValue(value, unit)


	def __init__(self, value, unit):
		self.value = value
		self.unit = unit


	def __str__(self):
		return str(self.value) + ' ' + str(self.unit)


	def asUnit(self, unit):
		if self.unit.getQuantity() != unit.getQuantity():
			raise Exception(
				'Expected a unit compatible with %s; got %s as unit' % (
				str(unit), str(self.unit)
				))
		multiplier = self.unit.getMultiplier() / unit.getMultiplier()
		return UnitValue(
			self.value *multiplier.numerator / multiplier.denominator,
			unit
			)

