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

import sqlite3

from log import log



class StoredObject:
	@staticmethod
	def create(storage, tableName, **kwargs):
		names = list(kwargs.keys())
		values = [kwargs[k] for k in names]
		questionMarks = ','.join(['?'] * len(kwargs))

		names = ['`%s`' % n for n in names]
		query = 'INSERT INTO %s (%s) VALUES (%s)' % (tableName, ','.join(names), questionMarks)

		cursor = storage.execute(query, values)
		ID = cursor.lastrowid

		return ID


	def __init__(self, storage, tableName, ID):
		self._storage = storage
		self._tableName = tableName
		query = 'SELECT * from %s WHERE `ID` = ?' % tableName

		cursor = self._storage.execute(query, (ID,))
		values = cursor.fetchone()
		names = [x[0] for x in cursor.description]

		for name, value in zip(names, values):
			setattr(self, name, value)


	def update(self, **kwargs):
		names = list(kwargs.keys())
		values = [kwargs[k] for k in names]
		questionMarks = ','.join(['?'] * len(kwargs))

		quotedNames = ['`%s`' % n for n in names]
		query = 'UPDATE %s SET (%s) = (%s) WHERE `ID` = ?' % \
			(self._tableName, ','.join(quotedNames), questionMarks)

		self._storage.execute(query, values + [self.ID])

		#Local update:
		for name, value in zip(names, values):
			setattr(self, name, value)


	def delete(self):
		query = 'DELETE FROM %s WHERE `ID` = ?' % self._tableName
		cursor = self._storage.execute(query, (self.ID,))



class Storage:
	def __init__(self, filename):
		self.connection = sqlite3.connect(filename)
		self.execute('PRAGMA foreign_keys = ON')
		self.makeTables()


	def shutdown(self):
		self.connection.close()


	def makeTables(self):
		cursor = self.connection.cursor()
		cursor.execute(
			'CREATE TABLE IF NOT EXISTS `buyOrders` ('
			'	`ID`        INTEGER,'
			'	`limitRate` INTEGER,'
			'	`amount`    INTEGER,'
			'	`status`    INTEGER,'
			'	PRIMARY KEY(`ID`)'
			')'
			)
		cursor.execute(
			'CREATE TABLE IF NOT EXISTS `sellOrders` ('
			'	`ID`        INTEGER,'
			'	`limitRate` INTEGER,'
			'	`amount`    INTEGER,'
			'	`status`    INTEGER,'
			'	PRIMARY KEY(`ID`)'
			')'
			)
		cursor.execute(
			'CREATE TABLE IF NOT EXISTS `counterOffers` ('
			'	`ID`   INTEGER,'
			'	`blob` BLOB,'
			'	PRIMARY KEY(`ID`)'
			')'
			)
		cursor.execute(
			'CREATE TABLE IF NOT EXISTS `buyTransactions` ('
			'	`ID`              INTEGER,'
			'	`buyOrder`        INTEGER,'
			'	`status`          INTEGER,'
			'	`fiatAmount`      INTEGER,'
			'	`cryptoAmount`    INTEGER,'
			'	`paymentHash`     BLOB,'
			'	`paymentPreimage` BLOB,'
			'	PRIMARY KEY(`ID`),'
			'	FOREIGN KEY(`buyOrder`) REFERENCES buyOrders(ID)'
			')'
			)
		cursor.execute(
			'CREATE TABLE IF NOT EXISTS `sellTransactions` ('
			'	`ID`                    INTEGER,'
			'	`sellOrder`             INTEGER,'
			'	`counterOffer`          INTEGER,'
			'	`status`                INTEGER,'
			'	`senderFiatAmount`      INTEGER,'
			'	`receiverFiatAmount`    INTEGER,'
			'	`maxSenderCryptoAmount` INTEGER,'
			'	`senderCryptoAmount`    INTEGER,'
			'	`receiverCryptoAmount`  INTEGER,'
			'	`senderTimeoutDelta`    INTEGER,'
			'	`lockedTimeoutDelta`    INTEGER,'
			'	`CLTVExpiryDelta`       INTEGER,'
			'	`paymentHash`           BLOB,'
			'	`paymentPreimage`       BLOB,'
			'	PRIMARY KEY(`ID`),'
			'	FOREIGN KEY(`sellOrder`)    REFERENCES sellOrders(ID),'
			'	FOREIGN KEY(`counterOffer`) REFERENCES counterOffers(ID)'
			')'
			)
		self.connection.commit()


	def execute(self, query, values=[]):
		log('SQL query %s; values %s' % (query, values))
		cursor = self.connection.cursor()
		cursor.execute(query, values)
		self.connection.commit()
		return cursor



def main(): #pragma: nocover
	s = Storage('node0.bl4p.db')

	ID = StoredObject.create(s, 'buyOrders', amount=0)

	so = StoredObject(s, 'buyOrders', ID)

	so.update(limitRate=100)

	so.delete()

	s.shutdown()



if __name__ == "__main__":
	main() #pragma: nocover

