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



class Storage:
	def __init__(self):
		#TODO: persistent storage of orders and transactions
		self.orders = {}         #localID -> order
		self.remoteOfferIDs = {} #localID -> remoteID
		self.nextLocalOrderID = 0
		self.transactions = {}   #localID -> transaction
		self.nextLocalTransactionID = 0


	def addOrder(self, newOrder):
		ID = self.nextLocalOrderID

		#TODO: handle 32-bit overflow.
		#In the offer structure and in the Lightning payload,
		#only 32 bits are reserved for the ID.
		self.nextLocalOrderID += 1

		newOrder.ID = ID
		self.orders[ID] = newOrder


	def getOrderIDs(self):
		return self.orders.keys()


	def getOrder(self, ID):
		return self.orders[ID]


	def getRemoteOfferID(self, ID):
		try:
			return self.remoteOfferIDs[ID]
		except KeyError:
			return None


	def setRemoteOfferID(self, ID, remoteOfferID):
		self.remoteOfferIDs[ID] = remoteOfferID


	def updateOrderStatus(self, ID, status):
		self.orders[ID].status = status


	def addTransaction(self, newTransaction):
		ID = self.nextLocalTransactionID
		self.nextLocalTransactionID += 1
		self.transactions[ID] = newTransaction

