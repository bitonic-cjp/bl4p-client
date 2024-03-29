#!/usr/bin/env python3
#    Copyright (C) 2018-2021 by Bitonic B.V.
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

import base64
import decimal
import hashlib
import os
import sys
import traceback

from lightningd import lightning
import secp256k1



sha256 = lambda preimage: hashlib.sha256(preimage).digest()
sha512 = lambda preimage: hashlib.sha512(preimage).digest()



socketPath = sys.argv[1]

rpc = lightning.LightningRpc(socketPath)

fiatCurrency   = rpc.call('bl4p.getfiatcurrency')
cryptoCurrency = rpc.call('bl4p.getcryptocurrency')
fiatName      = fiatCurrency['name']
fiatDivisor   = fiatCurrency['divisor']
cryptoName    = cryptoCurrency['name']
cryptoDivisor = cryptoCurrency['divisor']


def cmd_buy():
	'Add a buy order'
	limitRate = input('Limit exchange rate (%s/%s)? ' % (fiatName, cryptoName))
	limitRate = int(decimal.Decimal(limitRate) * fiatDivisor)
	amount = input('Maximum amount (%s)? ' % fiatName)
	amount = int(decimal.Decimal(amount) * fiatDivisor)
	return rpc.call('bl4p.buy', {'limit_rate': limitRate, 'amount': amount})


def cmd_sell():
	'Add a sell order'
	limitRate = input('Limit exchange rate (%s/%s)? ' % (fiatName, cryptoName))
	limitRate = int(decimal.Decimal(limitRate) * fiatDivisor)
	amount = input('Maximum amount (%s)? ' % cryptoName)
	amount = int(decimal.Decimal(amount) * cryptoDivisor)
	return rpc.call('bl4p.sell', {'limit_rate': limitRate, 'amount': amount})


def cmd_list():
	'List open orders'
	return rpc.call('bl4p.list', {})


def cmd_cancel():
	'Cancel an open order'
	orderList = rpc.call('bl4p.list', {})
	orderList = orderList['sell'] + orderList['buy']
	orderList.sort(key = lambda o: o['ID'])
	if not orderList:
		print('There are no open orders to be canceled')
		return
	for order in orderList:
		print(order)
	ID = int(input('ID of order to cancel: '))
	return rpc.call('bl4p.cancel', {'orderID': ID})


def cmd_login():
	'Change BL4P login settings'
	#TODO (bug 14): make URL configurable
	url = 'ws://localhost:8000/'

	currentConfig = rpc.call('bl4p.getconfig', {})['values']

	signingPrivateKeyHex = currentConfig['bl4p.signingPrivateKey']
	if signingPrivateKeyHex == '':
		print('We don\'t have a signing key yet; generating a new one.')
		signingPrivateKeyHex = os.urandom(32).hex()
		rpc.call('bl4p.setconfig', {'values': {
			'bl4p.signingPrivateKey': signingPrivateKeyHex,
			}})

	pk = secp256k1.PrivateKey(privkey=bytes.fromhex(signingPrivateKeyHex))
	signingPublicKey = pk.pubkey.serialize()
	print('Public key (hex-encoded): ', signingPublicKey.hex())

	apiKey = input('API key? ')
	apiSecret = input('API secret (base64-encoded): ')

	return rpc.call('bl4p.setconfig', {'values': {
		'bl4p.url'              : url,
		'bl4p.apiKey'           : apiKey,
		'bl4p.apiSecret'        : apiSecret,
		}})


def cmd_stop():
	'Terminate application.'
	sys.exit()


def cmd_help():
	'Display this message.'
	names = list(commands.keys())
	names.sort()
	maxLen = max(map(len, names))
	for name in names:
		printedName = name.ljust(maxLen, ' ')
		description = commands[name].__doc__
		print('%s: %s' % (printedName, description))


def cmd_license():
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
'exit'    : cmd_stop,
'stop'    : cmd_stop,
'quit'    : cmd_stop,
'help'    : cmd_help,
'license' : cmd_license,
'buy'     : cmd_buy,
'sell'    : cmd_sell,
'list'    : cmd_list,
'cancel'  : cmd_cancel,
'login'   : cmd_login,
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

	ret = cmd()
	if ret is not None:
		print(ret)


print('''
BL4P Client Copyright (C) 2018-2021 Bitonic B.V.
Enter 'help' for a list of commands. Enter 'license' for licensing information.
''')

while True:
	cmd = input('> ')
	try:
		handleCommand(cmd)
	except Exception:
		print(traceback.format_exc())

