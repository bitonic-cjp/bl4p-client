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



class Lightning:
	def __init__(self):
		pass


	def getCurrency(self):
		return 'btc'


	def getDivisor(self):
		# mBTC:
		return 100000000000


	def startTransaction(self,
		destinationNodeID, paymentHash,
		recipientCryptoAmount, maxSenderCryptoAmount,
		fiatAmount, fiatCurrency, fiatExchange):

		pass


	def close(self):
		pass

