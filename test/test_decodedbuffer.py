#    Copyright (C) 2019 by Bitonic B.V.
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

sys.path.append('..')

import decodedbuffer



class TestDecodedBuffer(unittest.TestCase):
	def test_append(self):
		b = decodedbuffer.DecodedBuffer('UTF-8')
		b.append(b'Corn\xc3')
		self.assertEqual(b.get(), 'Corn')
		self.assertEqual(b.get(), 'Corn')

		b.append(b'\xa9 Plooy')
		self.assertEqual(b.get(), 'Corné Plooy')

		b = decodedbuffer.DecodedBuffer('UTF-8')
		b.append(b'\xe2\x82')
		self.assertEqual(b.get(), '')
		b.append(b'\xac')
		self.assertEqual(b.get(), '€')


	def test_set(self):
		b = decodedbuffer.DecodedBuffer('UTF-8')
		b.append(b'Hello Corn\xc3')
		self.assertEqual(b.get(), 'Hello Corn')

		b.set(b.get()[6:])

		self.assertEqual(b.get(), 'Corn')
		b.append(b'\xa9')
		self.assertEqual(b.get(), 'Corné')



if __name__ == '__main__':
	unittest.main(verbosity=2)

