#    Copyright (C) 2020-2021 by Bitonic B.V.
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

import sys
import unittest

from utils import MockCursor, MockStorage

sys.path.append('..')

import configuration



class TestConfiguration(unittest.TestCase):
	def test_startup(self):
		storage = MockStorage()
		storage.configuration['bl4p.url'] = 'PresetURL'
		conf = configuration.Configuration(storage)

		self.assertEqual(conf.values,
			{
			'bl4p.url'              : 'PresetURL',
			'bl4p.apiKey'           : '',
			'bl4p.apiSecret'        : '',
			'bl4p.signingPrivateKey': '',
			})
		self.assertEqual(storage.configuration, conf.values)


	def test_getset(self):
		storage = MockStorage()
		conf = configuration.Configuration(storage)

		self.assertEqual(conf.getValue('bl4p.apiKey'), '')

		conf.setValue('bl4p.apiKey', 'foo')			

		self.assertEqual(storage.configuration['bl4p.apiKey'], 'foo')
		self.assertEqual(conf.getValue('bl4p.apiKey'), 'foo')



if __name__ == '__main__':
	unittest.main(verbosity=2)

