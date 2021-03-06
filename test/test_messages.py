#    Copyright (C) 2019-2020 by Bitonic B.V.
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
from unittest.mock import Mock

sys.path.append('..')

import messages



class Dummy:
	pass



class TestMessages(unittest.TestCase):
	def test_Handler(self):
		m = Mock()
		h = messages.Handler({Dummy: m})

		obj = Dummy()
		h.handleMessage(obj)
		m.assert_called_once_with(obj)

		with self.assertRaises(messages.NoMessageHandler):
			h.handleMessage('foobar')


	def test_Router_immediateForwarding(self):
		m = Mock()
		h = messages.Handler({Dummy: m})
		r = messages.Router()
		obj = Dummy()

		r.addHandler(h)
		r.startMessaging()
		r.handleMessage(obj)

		m.assert_called_once_with(obj)

		#Cannot have two handlers handling the same message class:
		h2 = messages.Handler({Dummy: m})
		with self.assertRaises(Exception):
			r.addHandler(h2)


	def test_Router_delayedForwarding(self):
		m = Mock()
		h = messages.Handler({Dummy: m})
		r = messages.Router()
		obj = Dummy()

		r.handleMessage(obj)
		r.addHandler(h)
		r.startMessaging()

		m.assert_called_once_with(obj)



if __name__ == '__main__':
	unittest.main(verbosity=2)

