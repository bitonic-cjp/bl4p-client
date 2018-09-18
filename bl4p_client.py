#    Copyright (C) 2018 by Bitonic B.V.
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
		self.orders = []


	def close(self):
		self.connection.close()


	def addOrder(self, newOrder):
		self.orders.append(newOrder)

