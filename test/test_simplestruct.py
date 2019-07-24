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

import sys
import unittest

sys.path.append('..')

import simplestruct


class Foo(simplestruct.Struct):
	bar = 0
	baz = None



class TestStruct(unittest.TestCase):
	def test_construction(self):
		obj = Foo(bar=1, baz='z')
		self.assertEqual(obj.bar, 1)
		self.assertEqual(obj.baz, 'z')

		with self.assertRaises(KeyError):
			obj = Foo(x=0)

		with self.assertRaises(KeyError):
			obj = Foo(bar=0)

		with self.assertRaises(KeyError):
			obj = Foo(baz=0)


	def test_str(self):
		obj = Foo(bar='contents A', baz='contents B')
		s = str(obj)
		self.assertTrue('bar' in s)
		self.assertTrue('baz' in s)
		self.assertTrue('contents A' in s)
		self.assertTrue('contents B' in s)


	def test_eq(self):
		obj = Foo(bar=1, baz=2)
		self.assertEqual(obj, Foo(bar=1, baz=2))
		self.assertNotEqual(obj, Foo(bar=1, baz=3))
		self.assertNotEqual(obj, Foo(bar=3, baz=2))
		self.assertNotEqual(obj, Foo(bar=3, baz=4))



if __name__ == '__main__':
	unittest.main(verbosity=2)

