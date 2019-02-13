#!/usr/bin/env python3
#    Copyright (C) 2018-2019 by Bitonic B.V.
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

from lightningd import lightning

socketPath = sys.argv[1]

rpc = lightning.LightningRpc(socketPath)


def stop():
	'Terminate application.'
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


commands = \
{
'exit'    : stop,
'stop'    : stop,
'quit'    : stop,
'help'    : help,
'license' : license,
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
BL4P Client Copyright (C) 2018-2019 Bitonic B.V.
Enter 'help' for a list of commands. Enter 'license' for licensing information.
''')

while True:
	cmd = input('> ')
	try:
		handleCommand(cmd)
	except Exception as e:
		print(str(e))

