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

import asyncio
import os
import signal
import sys

import backend
import bl4p_interface
import messages
import plugin_interface



async_stdio = None
async def stdio():
	global async_stdio
	if async_stdio is not None:
		return async_stdio

	loop = asyncio.get_event_loop()

	reader = asyncio.StreamReader(
		limit=asyncio.streams._DEFAULT_LIMIT,
		loop=loop
		)
	await loop.connect_read_pipe(
		lambda: asyncio.StreamReaderProtocol(reader, loop=loop),
		sys.stdin
		)

	writer_transport, writer_protocol = await loop.connect_write_pipe(
		lambda: asyncio.streams.FlowControlMixin(loop=loop),
		os.fdopen(sys.stdout.fileno(), 'wb')
		)
	writer = asyncio.streams.StreamWriter(
		writer_transport, writer_protocol, None, loop
		)

	async_stdio = reader, writer
	return async_stdio



class BL4PClient:
	def __init__(self):
		self.backend = backend.Backend()


	async def startup(self):
		stdin, stdout = await stdio()
		self.pluginInterface = plugin_interface.PluginInterface(self, stdin, stdout)
		self.pluginInterface.startup()

		self.bl4pInterface = bl4p_interface.BL4PInterface()
		await self.bl4pInterface.startup('ws://localhost:8000/', '3', '3')

		self.backend.setLNAddress(  'LNdummy'  ) #TODO: get from RPC interface
		self.backend.setBL4PAddress('BL4Pdummy') #TODO: get from RPC interface


	async def shutdown(self):
		await self.bl4pInterface.shutdown()
		await self.pluginInterface.shutdown()


	def handleIncomingMessage(self, message):
		#Process a single incoming message:
		self.backend.handleIncomingMessage(message)

		#Process queue of outgoing messages:
		while True:
			try:
				message = self.backend.getNextOutgoingMessage()
			except IndexError:
				break #no more outgoing messages

			#TODO: have interfaces register their message types
			if message.__class__ in [messages.BL4PAddOffer]:
				self.bl4pInterface.sendOutgoingMessage(message)
			else:
				raise Exception('Unknown outgoing message type ' + str(message))



def terminateSignalHandler():
	loop = asyncio.get_event_loop()
	loop.stop()


client = BL4PClient()
loop = asyncio.get_event_loop()

loop.run_until_complete(client.startup())

loop.add_signal_handler(signal.SIGINT , terminateSignalHandler)
loop.add_signal_handler(signal.SIGTERM, terminateSignalHandler)
loop.run_forever()

loop.run_until_complete(client.shutdown())
loop.close()

