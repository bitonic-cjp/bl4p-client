#!/usr/bin/env python3
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

import decimal
import sys

import bl4p_client
from order import BuyOrder, SellOrder



client = bl4p_client.BL4PClient()



def stop():
	'Terminate application.'
	client.close()
	sys.exit()


def help():
	'Display this message.'
	names = list(commands.keys())
	names.sort()
	maxLen = max(map(len, names))
	for name in names:
		printedName = name.ljust(maxLen, ' ')
		description = commands[name].__doc__
		print('%s: %s' % (printedName, description))


def license():
	'Display licensing information.'
	print('''BL4P Client is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

BL4P Client is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with BL4P Client. If not, see <http://www.gnu.org/licenses/>.''')


def addOrder():
	'Add a limit order'

	typeName = input('buy or sell? ')
	typeName = typeName.strip().lower()
	if typeName not in ['buy', 'sell']:
		raise Exception('Invalid answer')

	limitRate = input('Limit exchange rate (EUR/BTC)? ')
	limitRate = decimal.Decimal(limitRate)

	if typeName == 'buy':
		order = BuyOrder(limitRate)
	elif typeName == 'sell':
		order = SellOrder(limitRate)

	#TODO: modify order settings

	client.addOrder(order)



commands = \
{
'stop'    : stop,
'quit'    : stop,
'help'    : help,
'license' : license,
'addorder': addOrder,
}

def handleCommand(cmd):
	cmd = cmd.strip() # remove whitespace

	if not cmd:
		return

	cmd = cmd.lower()

	try:
		cmd = commands[cmd]
	except KeyError:
		print('No such command: "%s". Enter "help" for a list of commands.' % cmd)
		return

	cmd()


print('''
BL4P Client Copyright (C) 2018
Enter 'help' for a list of commands. Enter 'license' for licensing information.
''')

while True:
	cmd = input('> ')
	try:
		handleCommand(cmd)
	except Exception as e:
		print(str(e))

