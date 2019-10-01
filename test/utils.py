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

import asyncio


#Transaction states:
STATUS_INITIAL = 0
STATUS_STARTED = 1
STATUS_LOCKED = 2
STATUS_RECEIVED_PREIMAGE = 3
STATUS_FINISHED = 4
STATUS_CANCELED = 5



def asynciotest(oldMethod):
	def newMethod(self):
		loop = asyncio.get_event_loop()
		return loop.run_until_complete(oldMethod(self))

	return newMethod



class DummyWriter:
	def __init__(self):
		self.buffer = b''


	def write(self, data):
		self.buffer += data



class DummyReader:
	def __init__(self):
		self.buffer = b''


	async def read(self, n):
		ret = self.buffer[:n]
		self.buffer = self.buffer[n:]
		return ret



class MockCursor(list):
	def __init__(self, data, **kwargs):
		list.__init__(self, data)
		for k,v in kwargs.items():
			setattr(self, k, v)

	def fetchone(self):
		return self.pop(0)



class MockStorage:
	def __init__(self, DBFile = None, test = None, init = lambda x: None, startCount = 61):
		self.test = test
		self.DBFile = DBFile
		self.reset(startCount)
		init(self)


	def reset(self, startCount):
		self.buyOrders = {}
		self.buyTransactions = {}
		self.sellOrders = {}
		self.sellTransactions = {}
		self.counterOffers = {}
		self.counter = startCount


	def execute(self, query, data=[]):
		if query.startswith('INSERT INTO buyTransactions'):
			names = query[query.index('(')+1:query.index(')')]
			names = names.replace('`','').split(',')
			self.test.assertEqual(len(names), len(data))
			self.buyTransactions[self.counter] = \
			{
			names[i]:data[i]
			for i in range(len(names))
			}
			self.buyTransactions[self.counter]['ID'] = self.counter
			self.counter += 1
			return MockCursor([], lastrowid=self.counter-1)
		elif query.startswith('UPDATE buyTransactions SET'):
			ID = data[-1]
			data = data[:-1]
			names = query[query.index('(')+1:query.index(')')]
			names = names.replace('`','').split(',')
			self.test.assertEqual(len(names), len(data))
			for i in range(len(names)):
				self.buyTransactions[ID][names[i]] = data[i]
			return MockCursor([])
		elif query == 'SELECT * from buyTransactions WHERE `ID` = ?':
			data = self.buyTransactions[data[0]]
			keys = list(data.keys())
			values = [data[k] for k in keys]
			return MockCursor([values], description=[(k,) for k in keys])
		elif query == 'SELECT ID from buyTransactions WHERE buyOrder = ? AND status != ? AND status != ?':
			self.test.assertEqual(data[1:], [STATUS_FINISHED, STATUS_CANCELED])
			values = \
			[
			[tx['ID']]
			for tx in self.buyTransactions.values()
			if tx['buyOrder'] == data[0] and tx['status'] not in [STATUS_FINISHED, STATUS_CANCELED]
			]
			return MockCursor(values)

		elif query.startswith('INSERT INTO buyOrders'):
			names = query[query.index('(')+1:query.index(')')]
			names = names.replace('`','').split(',')
			self.test.assertEqual(len(names), len(data))
			self.buyOrders[self.counter] = \
			{
			names[i]:data[i]
			for i in range(len(names))
			}
			self.buyOrders[self.counter]['ID'] = self.counter
			self.counter += 1
			return MockCursor([], lastrowid=self.counter-1)
		elif query.startswith('UPDATE buyOrders SET'):
			ID = data[-1]
			data = data[:-1]
			names = query[query.index('(')+1:query.index(')')]
			names = names.replace('`','').split(',')
			self.test.assertEqual(len(names), len(data))
			for i in range(len(names)):
				self.buyOrders[ID][names[i]] = data[i]
			return MockCursor([])
		elif query == 'SELECT `ID` FROM `buyOrders` WHERE `status` = 0':
			self.test.assertEqual(data, [])
			return [[x] for x in self.buyOrders.keys()]
		elif query == 'SELECT * from buyOrders WHERE `ID` = ?':
			data = self.buyOrders[data[0]]
			keys = list(data.keys())
			values = [data[k] for k in keys]
			return MockCursor([values], description=[(k,) for k in keys])

		elif query.startswith('INSERT INTO sellTransactions'):
			names = query[query.index('(')+1:query.index(')')]
			names = names.replace('`','').split(',')
			self.test.assertEqual(len(names), len(data))
			self.sellTransactions[self.counter] = \
			{
			names[i]:data[i]
			for i in range(len(names))
			}
			self.sellTransactions[self.counter]['ID'] = self.counter
			self.counter += 1
			return MockCursor([], lastrowid=self.counter-1)
		elif query.startswith('UPDATE sellTransactions SET'):
			ID = data[-1]
			data = data[:-1]
			names = query[query.index('(')+1:query.index(')')]
			names = names.replace('`','').split(',')
			self.test.assertEqual(len(names), len(data))
			for i in range(len(names)):
				self.sellTransactions[ID][names[i]] = data[i]
			return MockCursor([])
		elif query == 'SELECT * from sellTransactions WHERE `ID` = ?':
			data = self.sellTransactions[data[0]]
			keys = list(data.keys())
			values = [data[k] for k in keys]
			return MockCursor([values], description=[(k,) for k in keys])
		elif query == 'SELECT ID from sellTransactions WHERE sellOrder = ? AND status != ? AND status != ?':
			self.test.assertEqual(data[1:], [STATUS_FINISHED, STATUS_CANCELED])
			values = \
			[
			[tx['ID']]
			for tx in self.sellTransactions.values()
			if tx['sellOrder'] == data[0] and tx['status'] not in [STATUS_FINISHED, STATUS_CANCELED]
			]
			return MockCursor(values)

		elif query.startswith('INSERT INTO sellOrders'):
			names = query[query.index('(')+1:query.index(')')]
			names = names.replace('`','').split(',')
			self.test.assertEqual(len(names), len(data))
			self.sellOrders[self.counter] = \
			{
			names[i]:data[i]
			for i in range(len(names))
			}
			self.sellOrders[self.counter]['ID'] = self.counter
			self.counter += 1
			return MockCursor([], lastrowid=self.counter-1)
		elif query.startswith('UPDATE sellOrders SET'):
			ID = data[-1]
			data = data[:-1]
			names = query[query.index('(')+1:query.index(')')]
			names = names.replace('`','').split(',')
			self.test.assertEqual(len(names), len(data))
			for i in range(len(names)):
				self.sellOrders[ID][names[i]] = data[i]
			return MockCursor([])
		elif query == 'SELECT `ID` FROM `sellOrders` WHERE `status` = 0':
			self.test.assertEqual(data, [])
			return [[x] for x in self.sellOrders.keys()]
		elif query == 'SELECT * from sellOrders WHERE `ID` = ?':
			data = self.sellOrders[data[0]]
			keys = list(data.keys())
			values = [data[k] for k in keys]
			return MockCursor([values], description=[(k,) for k in keys])

		elif query == 'INSERT INTO counterOffers (`blob`) VALUES (?)':
			self.counterOffers[self.counter] = \
			{
			'ID': self.counter,
			'blob': data[0],
			}
			self.counter += 1
			return MockCursor([], lastrowid=self.counter-1)
		elif query == 'SELECT * from counterOffers WHERE `ID` = ?':
			data = self.counterOffers[data[0]]
			keys = list(data.keys())
			values = [data[k] for k in keys]
			return MockCursor([values], description=[(k,) for k in keys])

		raise Exception('Query not recognized: ' + str(query))

