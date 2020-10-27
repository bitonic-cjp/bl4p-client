#    Copyright (C) 2020 by Bitonic B.V.
#
#    This file is part of the BL4P Client.
#
#    The BL4P Client is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    The BL4P Client is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with the BL4P Client. If not, see <http://www.gnu.org/licenses/>.

from typing import Dict, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
	import storage as storageModule #pragma: nocover



class Configuration:
	def __init__(self, storage: 'storageModule.Storage') -> None:
		self.storage = storage #type: storageModule.Storage

		defaultValues = \
		{
		'bl4p.url'       : '',
		'bl4p.username'  : '',
		'bl4p.password'  : '',
		'bl4p.privateKey': '',
		} #type: Dict[str, str]

		self.values = {} #type: Dict[str, str]
		cursor = self.storage.execute(
			'SELECT name, value from configuration') #type: storageModule.Cursor
		for element in cursor:
			name, value = element #type: Tuple[str, str]
			self.values[name] = value

		for name in defaultValues:
			if name not in self.values:
				value = defaultValues[name]
				self.storage.execute(
					'INSERT INTO configuration (name, value) VALUES (?, ?)',
					(name, value))
				self.values[name] = value


	def setValue(self, name: str, value: str) -> None:
		assert name in self.values
		
		self.storage.execute(
			'UPDATE configuration SET (value) = (?) WHERE `name` = ?',
			(value, name))
		self.values[name] = value


	def getValue(self, name: str) -> str:
		assert name in self.values

		return self.values[name]



def main() -> None: #pragma: nocover
	import storage as storageModule

	s = storageModule.Storage('node0.bl4p.db') #type: storageModule.Storage

	c = Configuration(s) #type: Configuration

	pw= c.getValue('bl4p.password')
	print(pw)
	pw += ' foo'
	c.setValue('bl4p.password', pw)
	pw= c.getValue('bl4p.password')
	print(pw)

	s.shutdown()



if __name__ == "__main__":
	main() #pragma: nocover

