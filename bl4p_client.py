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

import threading
import time

from bl4p_api import client as bl4p

import lightning
import order
import storage
from transaction import BuyTransaction, SellTransaction



def runInThread(implementationFunc):
	'''
	Function decorator, which can be used by Node methods to have them
	called by an external thread, but have them run inside the internal
	thread of the BL4PClient object.
	Intended for internal use by BL4PClient.
	Not intended to be part of the API.
	'''

	def remoteCaller(self, *args, **kwargs):
		with self._commandFunctionLock:
			self._commandFunction = (implementationFunc, args, kwargs)
			self._commandProcessed.clear()
		self._commandProcessed.wait()

		if isinstance(self._commandReturnValue, Exception):
			raise self._commandReturnValue
		return self._commandReturnValue

	remoteCaller.__doc__ = implementationFunc.__doc__

	return remoteCaller



class BL4PClient(threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self)

		#threading.Thread attribute:
		self.name = 'BL4PClient'

		self.storage = storage.Storage()

		self.__stop = False

		self._commandFunctionLock = threading.Lock()
		self._commandFunction = None
		self._commandProcessed = threading.Event()
		self._commandReturnValue = None


	def stop(self):
		'''
		Stops the BL4PClient thread.
		This method blocks until the BL4PClient object is stopped
		completely.
		'''

		self.__stop = True
		self.join()


	def run(self):
		'''
		The thread function.
		Intended for internal use by BL4PClient.
		Not intended to be part of the API.
		'''

		self.connection = bl4p.Bl4pApi('ws://localhost:8000/', '3', '3')
		self.lightning = lightning.Lightning()
		self.bl4pAmountDivisor = 10000 #TODO: query this from the server

		self.__stop = False
		while True:

			#API events:
			with self._commandFunctionLock:
				s = self._commandFunction
				if s is not None:
					try:
						self._commandReturnValue = s[0](self, *s[1], **s[2])
					except Exception as e:
						self._commandReturnValue = e
						#TODO: log exception
					self._commandProcessed.set()
					self._commandFunction = None

			if self.__stop:
				break

			#Syncing offers:
			self.syncOffers()

			#TODO: other event handling, and periodic activities
			time.sleep(0.1)

		self.lightning.close()
		self.connection.close()


	@runInThread
	def addOrder(self, newOrder):
		self.storage.addOrder(newOrder)


	def syncOffers(self):
		#sync from local orders to remote offers

		offersOnServer = self.connection.listOffers()
		#TODO: remove offers we don't have here
		#TODO: maybe replace offers for changed orders

		#Add new offers:
		for localID in self.storage.getOrderIDs():
			ownOrder = self.storage.getOrder(localID)

			#For all idle orders (new and existing), try to find matches:
			if ownOrder.status == order.STATUS_IDLE:
				self.searchInMarket(localID)

			#Place the offer on the market if it's not already there
			if self.storage.getRemoteOfferID(localID) is None:
				self.storage.setRemoteOfferID(localID,
					self.connection.addOffer(ownOrder)
					)
				#print('Local ID:', localID)
				#print('Remote ID:', self.storage.getRemoteOfferID(localID)


	def searchInMarket(self, localID):
		ownOrder = self.storage.getOrder(localID)
		counterOffers = self.connection.findOffers(ownOrder)

		#TODO: filter on sensibility (e.g. max >= min for all conditions)
		#TODO: check if offers actually match
		#TODO: filter counterOffers on acceptability
		#TODO: sort counterOffers (e.g. on exchange rate)

		if not counterOffers:
			return

		#Start trade on the first in the list
		self.doTrade(localID, counterOffers[0])


	def doTrade(self, localID, counterOffer):
		ownOrder = self.storage.getOrder(localID)

		if isinstance(ownOrder, order.BuyOrder):
			return
			#TODO: enable buyer-initiated trade once supported
			#tx = BuyTransaction(localID, counterOffer)
			#TODO: fill with offer data
		elif isinstance(ownOrder, order.SellOrder):
			tx = SellTransaction(localID, counterOffer)
			#TODO: fill with offer data
		else:
			raise Exception('Unsupported order type - cannot use it in trade')

		print('Doing trade for local order ID', localID)
		print('  local order: ', str(ownOrder))
		print('  counter offer: ', str(counterOffer))

		#Initiate first steps of the tx
		tx.initiate(self)

		self.storage.addTransaction(tx)
		self.storage.updateOrderStatus(localID, order.STATUS_TRADING)

