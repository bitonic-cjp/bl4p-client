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



class Storage:
	def __init__(self, filename):
		self.connection = sqlite3.connect(filename)

		cursor = self.connection.cursor()
		cursor.execute('PRAGMA foreign_keys = ON')
		self.connection.commit()

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
			'	PRIMARY KEY(`ID`)'
			')'
			)
		cursor.execute(
			'CREATE TABLE IF NOT EXISTS `sellOrders` ('
			'	`ID`        INTEGER,'
			'	`limitRate` INTEGER,'
			'	`amount`    INTEGER,'
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

