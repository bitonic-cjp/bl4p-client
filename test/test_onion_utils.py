#    Copyright (C) 2020 by Bitonic B.V.
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

import onion_utils



class TestOnionUtils(unittest.TestCase):
	def test_serializeBigsize(self):
		self.assertEqual(onion_utils.serializeBigsize(0x00), b'\x00')
		self.assertEqual(onion_utils.serializeBigsize(0xfc), b'\xfc')

		self.assertEqual(onion_utils.serializeBigsize(0x00fd), b'\xfd\x00\xfd')
		self.assertEqual(onion_utils.serializeBigsize(0xffff), b'\xfd\xff\xff')

		self.assertEqual(onion_utils.serializeBigsize(0x00010000), b'\xfe\x00\x01\x00\x00')
		self.assertEqual(onion_utils.serializeBigsize(0xffffffff), b'\xfe\xff\xff\xff\xff')

		self.assertEqual(onion_utils.serializeBigsize(0x0000000100000000), b'\xff\x00\x00\x00\x01\x00\x00\x00\x00')
		self.assertEqual(onion_utils.serializeBigsize(0xffffffffffffffff), b'\xff\xff\xff\xff\xff\xff\xff\xff\xff')


	def test_deserializeBigsize(self):
		self.assertEqual(onion_utils.deserializeBigsize(b'\x00Foobar'), (0x00, b'Foobar'))
		self.assertEqual(onion_utils.deserializeBigsize(b'\xfcFoobar'), (0xfc, b'Foobar'))

		self.assertEqual(onion_utils.deserializeBigsize(b'\xfd\x00\xfdFoobar'), (0x00fd, b'Foobar'))
		self.assertEqual(onion_utils.deserializeBigsize(b'\xfd\xff\xffFoobar'), (0xffff, b'Foobar'))

		self.assertEqual(onion_utils.deserializeBigsize(b'\xfe\x00\x01\x00\x00Foobar'), (0x00010000, b'Foobar'))
		self.assertEqual(onion_utils.deserializeBigsize(b'\xfe\xff\xff\xff\xffFoobar'), (0xffffffff, b'Foobar'))

		self.assertEqual(onion_utils.deserializeBigsize(b'\xff\x00\x00\x00\x01\x00\x00\x00\x00Foobar'), (0x0000000100000000, b'Foobar'))
		self.assertEqual(onion_utils.deserializeBigsize(b'\xff\xff\xff\xff\xff\xff\xff\xff\xffFoobar'), (0xffffffffffffffff, b'Foobar'))


	def test_serializeTLVPayload(self):
		self.assertEqual(
			onion_utils.serializeTLVPayload({0x21: b'Foo', 0xcafebabe: b'Bar'}),
			b'\x0e\x21\x03Foo\xfe\xca\xfe\xba\xbe\x03Bar'
			)


	def test_deserializeTLVPayload(self):
		self.assertEqual(
			onion_utils.deserializeTLVPayload(b'\x0e\x21\x03Foo\xfe\xca\xfe\xba\xbe\x03Bar'),
			{0x21: b'Foo', 0xcafebabe: b'Bar'}
			)


	def test_serializeStandardPayload(self):
		#Example taken from C-Lightning's createonion documentation:
		self.assertEqual(
			onion_utils.serializeStandardPayload(
				{
				'channel': '103x1x1',
				'msatoshi': 1001,
				'delay': 15,
				'style': 'legacy',
				},
				108,
				),
			bytes.fromhex(
				'00000067000001000100000000000003e90000007b000000000000000000000000000000000000000000000000'
				))

		with self.assertRaises(Exception):
			onion_utils.serializeStandardPayload(
				{
				'channel': '103x1x1',
				'msatoshi': 1001,
				'delay': 15,
				'style': 'Not so legacy',
				},
				108,
				)


	def test_makeCreateOnionHopsData(self):
		self.assertEqual(
			onion_utils.makeCreateOnionHopsData(
				[
				{
				'id': '022d223620a359a47ff7f7ac447c85c46c923da53389221a0054c11c1e3ca31d59',
				'channel': '103x2x1',
				'msatoshi': 1002,
				'delay': 21,
				'style': 'legacy',
				},
				{
				'id': '035d2b1192dfba134e10e540875d366ebc8bc353d5aa766b80c090b39c3a5d885d',
				'channel': '103x1x1',
				'msatoshi': 1001,
				'delay': 15,
				'style': 'legacy',
				},
				],
				b'\xca\xfe\xba\xbe',
				108
				),
			[
			{
			'pubkey': '022d223620a359a47ff7f7ac447c85c46c923da53389221a0054c11c1e3ca31d59',
			'payload': '00000067000001000100000000000003e90000007b000000000000000000000000000000000000000000000000',
			},
			{
			'pubkey': '035d2b1192dfba134e10e540875d366ebc8bc353d5aa766b80c090b39c3a5d885d',
			'payload': '0afe424c345004cafebabe',
			}
			])



if __name__ == '__main__':
	unittest.main(verbosity=2)

