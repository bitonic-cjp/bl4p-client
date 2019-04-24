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

import ln_payload



class TestPayload(unittest.TestCase):
	def test_payload(self):
		p1 = ln_payload.Payload(fiatAmount=0xf1f2f3f4f5f6f7f8, offerID=0xc1c2c3c4)
		self.assertEqual(p1.fiatAmount, 0xf1f2f3f4f5f6f7f8)
		self.assertEqual(p1.offerID, 0xc1c2c3c4)

		s = p1.encode()
		self.assertTrue(isinstance(s, bytes))
		self.assertEqual(s, b'\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xc1\xc2\xc3\xc4')

		p2 = ln_payload.Payload.decode(s)
		self.assertEqual(p2.fiatAmount, 0xf1f2f3f4f5f6f7f8)
		self.assertEqual(p2.offerID, 0xc1c2c3c4)



if __name__ == '__main__':
	unittest.main(verbosity=2)

