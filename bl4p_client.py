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

from bl4p_api import client as bl4p



class BL4PClient:
	def __init__(self):
		self.connection = bl4p.Bl4pApi('ws://localhost:8000/', '3', '3')

		self.orders = [] #Every item is (offerID, order)


	def close(self):
		self.connection.close()


	def addOrder(self, newOrder):
		self.orders.append((None, newOrder))
		self.syncOffers()


	def syncOffers(self):
		#sync from local orders to remote offers

		offersOnServer = self.connection.listOffers()
		#TODO: remove offers we don't have here
		#TODO: maybe replace offers for changed orders

		#Add new offers:
		for i in range(len(self.orders)):
			ID, order = self.orders[i]
			if ID is None:
				ID = self.connection.addOffer(order)
				self.orders[i] = ID, order

