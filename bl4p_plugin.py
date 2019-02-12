#!/usr/bin/env python3
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


#sys.stderr.write('    Debug: Started\n')
while True:
	x = sys.stdin.readline()
	#sys.stderr.write('    Debug: Got input: %s\n' % x)
	sys.stdout.write('Got input: %s\n' % x)
	sys.stdout.flush()
	#sys.stderr.write('    Debug: Wrote output\n')

