#    Copyright (C) 2019 by Bitonic B.V.
#
#    This file is part of BL4P Client.
#
#    BL4P Client is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    BL4P Client is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with BL4P Client. If not, see <http://www.gnu.org/licenses/>.

import os
import sys
import unittest

sys.path.append('..')

import storage



class TestStorage(unittest.TestCase):
	def setUp(self):
		self.filename = '_test.db'
		try:
			os.remove(self.filename)
		except FileNotFoundError:
			pass
		self.storage = storage.Storage(self.filename)


	def tearDown(self):
		self.storage.shutdown()
		os.remove(self.filename)


	def test_storageCreation(self):
		cursor = self.storage.execute('SELECT name,sql FROM sqlite_master')

		tables = {}
		for table in cursor:
			name, sql = table

			#Simplify whitespace
			sql = ' '.join(sql.split())

			tables[name] = sql

		#Ignore the presence of other tables
		self.assertEqual(tables['buyOrders'],        'CREATE TABLE `buyOrders` ( `ID` INTEGER, `limitRate` INTEGER, `amount` INTEGER, PRIMARY KEY(`ID`))')
		self.assertEqual(tables['sellOrders'],       'CREATE TABLE `sellOrders` ( `ID` INTEGER, `limitRate` INTEGER, `amount` INTEGER, PRIMARY KEY(`ID`))')
		self.assertEqual(tables['counterOffers'],    'CREATE TABLE `counterOffers` ( `ID` INTEGER, `blob` BLOB, PRIMARY KEY(`ID`))')
		self.assertEqual(tables['buyTransactions'],  'CREATE TABLE `buyTransactions` ( `ID` INTEGER, `buyOrder` INTEGER, `status` INTEGER, `fiatAmount` INTEGER, `cryptoAmount` INTEGER, `paymentHash` BLOB, `paymentPreimage` BLOB, PRIMARY KEY(`ID`), FOREIGN KEY(`buyOrder`) REFERENCES buyOrders(ID))')
		self.assertEqual(tables['sellTransactions'], 'CREATE TABLE `sellTransactions` ( `ID` INTEGER, `sellOrder` INTEGER, `counterOffer` INTEGER, `status` INTEGER, `senderFiatAmount` INTEGER, `receiverFiatAmount` INTEGER, `maxSenderCryptoAmount` INTEGER, `senderCryptoAmount` INTEGER, `receiverCryptoAmount` INTEGER, `senderTimeoutDelta` INTEGER, `lockedTimeoutDelta` INTEGER, `CLTVExpiryDelta` INTEGER, `paymentHash` BLOB, `paymentPreimage` BLOB, PRIMARY KEY(`ID`), FOREIGN KEY(`sellOrder`) REFERENCES sellOrders(ID), FOREIGN KEY(`counterOffer`) REFERENCES counterOffers(ID))')


	def test_persistency(self):
		self.storage.execute('INSERT INTO `buyOrders` (`limitRate`, `amount`) VALUES (1234, 1)')

		self.storage.shutdown()
		self.storage = storage.Storage(self.filename)

		cursor = self.storage.execute('SELECT limitRate,amount FROM buyOrders')
		values = list(cursor)
		self.assertEqual(len(values), 1)
		limitRate,amount = values[0]
		self.assertEqual(limitRate, 1234)
		self.assertEqual(amount, 1)


	def test_storedObject(self):
		returnedID = storage.StoredObject.create(self.storage, 'buyOrders', limitRate=1234)

		cursor = self.storage.execute('SELECT ID,limitRate,amount FROM buyOrders')
		values = list(cursor)
		self.assertEqual(len(values), 1)
		ID,limitRate,amount = values[0]
		self.assertEqual(ID, returnedID)
		self.assertEqual(limitRate, 1234)
		self.assertEqual(amount, None)

		so = storage.StoredObject(self.storage, 'buyOrders', returnedID)
		self.assertEqual(so.ID, returnedID)
		self.assertEqual(so.limitRate, 1234)
		self.assertEqual(so.amount, None)

		so.update(limitRate=2000, amount=6)
		self.assertEqual(so.ID, returnedID)
		self.assertEqual(so.limitRate, 2000)
		self.assertEqual(so.amount, 6)

		cursor = self.storage.execute('SELECT ID,limitRate,amount FROM buyOrders')
		values = list(cursor)
		self.assertEqual(len(values), 1)
		ID,limitRate,amount = values[0]
		self.assertEqual(ID, returnedID)
		self.assertEqual(limitRate, 2000)
		self.assertEqual(amount, 6)

		so.delete()

		cursor = self.storage.execute('SELECT ID,limitRate,amount FROM buyOrders')
		values = list(cursor)
		self.assertEqual(len(values), 0)



if __name__ == '__main__':
	unittest.main(verbosity=2)

