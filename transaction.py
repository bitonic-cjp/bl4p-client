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

class Transaction:
	def __init__(self, localOrderID, counterOffer):
		self.localOrderID = localOrderID
		self.counterOffer = counterOffer



class BuyTransaction(Transaction):
	def __init__(self, localOrderID, counterOffer):
		Transaction.__init__(self, localOrderID, counterOffer)
		print('Created buy tx')



class SellTransaction(Transaction):
	def __init__(self, localOrderID, counterOffer):
		Transaction.__init__(self, localOrderID, counterOffer)
		print('Created sell tx')

