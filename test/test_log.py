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

import io
import os
import sys
import unittest

sys.path.append('..')

import log



class TestLog(unittest.TestCase):

	def test_standardLogOutput(self):
		self.assertEqual(log.logFile, sys.stderr)


	def test_writingLogLines(self):
		oldLogFile = log.logFile
		try:
			log.logFile = io.StringIO()
			log.log('Foobar')
			self.assertTrue('Foobar' in log.logFile.getvalue())

			log.logFile = io.StringIO()
			try:
				raise Exception('Test exception')
			except:
				log.logException()
			self.assertTrue('Test exception' in log.logFile.getvalue())
			self.assertTrue('test_writingLogLines' in log.logFile.getvalue())

		finally:
			log.logFile = oldLogFile


	def test_setLogFile(self):
		oldLogFile = log.logFile
		try:
			filename = '_testLogFile'
			log.setLogFile(filename)
			log.log('foo')

			#Inspect contents while it is still open, to verify flushing
			with open(filename, 'r') as f:
				self.assertTrue('foo' in f.read())

			log.logFile.close()
			os.remove(filename)
		finally:
			log.logFile = oldLogFile


if __name__ == '__main__':
	unittest.main(verbosity=2)

