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

		#TODO: persistent storage of orders
		self.orders = {}         #localID -> order
		self.remoteOfferIDs = {} #localID -> remoteID
		self.nextLocalID = 0

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

		self.connection.close()


	@runInThread
	def addOrder(self, newOrder):
		ID = self.nextLocalID
		self.nextLocalID += 1
		self.orders[ID] = newOrder


	def syncOffers(self):
		#sync from local orders to remote offers

		offersOnServer = self.connection.listOffers()
		#TODO: remove offers we don't have here
		#TODO: maybe replace offers for changed orders

		#Add new offers:
		for localID, order in self.orders.items():
						
			#Place the offer on the market if it's not already there
			if localID not in self.remoteOfferIDs:
				self.remoteOfferIDs[localID] = \
					self.connection.addOffer(order)
				#print('Local ID:', localID)
				#print('Remote ID:', self.remoteOfferIDs[localID])

