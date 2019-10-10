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
from typing import Tuple

import backend
import bl4p_interface
import messages
from log import log, setLogFile
import plugin_interface
import rpc_interface



async_stdio = None #type: Tuple[asyncio.StreamReader, asyncio.streams.StreamWriter]
async def stdio() -> Tuple[asyncio.StreamReader, asyncio.streams.StreamWriter]:
	global async_stdio
	if async_stdio is not None:
		return async_stdio

	loop = asyncio.get_event_loop() #type: asyncio.AbstractEventLoop

	reader = asyncio.StreamReader(loop=loop) #type: asyncio.StreamReader
	coro = loop.connect_read_pipe(
		lambda: asyncio.StreamReaderProtocol(reader, loop=loop),
		sys.stdin
		)
	await coro #type: ignore #mypy bug: it doesn't know this is a coroutine

	proto_factory = lambda: asyncio.streams.FlowControlMixin(loop=loop) #type: ignore #mypy bug: it doesn't know the loop argument
	coro = loop.connect_write_pipe(
		proto_factory,
		os.fdopen(sys.stdout.fileno(), 'wb')
		)
	writer_transport, writer_protocol = await coro #type: ignore #mypy bug: it doesn't know this is a coroutine

	writer = asyncio.streams.StreamWriter(
		writer_transport, writer_protocol, None, loop
		) #type: asyncio.streams.StreamWriter

	async_stdio = reader, writer
	return async_stdio



class BL4PClient:
	def __init__(self) -> None:
		self.backend = backend.Backend(self) #type: backend.Backend
		self.messageRouter = messages.Router() #type: messages.Router


	async def startup(self) -> None:
		stdin, stdout = await stdio() #type: Tuple[asyncio.StreamReader, asyncio.streams.StreamWriter]
		self.pluginInterface = plugin_interface.PluginInterface(self, stdin, stdout) #type: plugin_interface.PluginInterface
		await self.pluginInterface.startup() #Guarantees that init is called

		setLogFile(self.pluginInterface.logFile)

		reader, writer = await asyncio.open_unix_connection(path=self.pluginInterface.RPCPath) #type: ignore #mypy bug: it doesn't know open_unix_connection
		self.rpcInterface = rpc_interface.RPCInterface(self, reader, writer) #type: rpc_interface.RPCInterface
		await self.rpcInterface.startupRPC() #Gets our LN node ID

		self.bl4pInterface = bl4p_interface.BL4PInterface(self) #type: bl4p_interface.BL4PInterface
		#TODO (bug 14): make URL configurable
		#TODO (bug 15): make user/pass configurable
		await self.bl4pInterface.startup('ws://localhost:8000/', '3', '3')

		self.backend.setLNAddress(self.rpcInterface.nodeID)
		#TODO (bug 16): get address from BL4P
		self.backend.setBL4PAddress('BL4Pdummy')
		self.backend.startup(self.pluginInterface.DBFile)

		self.messageRouter.addHandler(self.backend)
		self.messageRouter.addHandler(self.pluginInterface)
		self.messageRouter.addHandler(self.bl4pInterface)
		self.messageRouter.addHandler(self.rpcInterface)


	async def shutdown(self) -> None:
		await self.backend.shutdown()
		await self.bl4pInterface.shutdown()
		await self.rpcInterface.shutdown()
		await self.pluginInterface.shutdown()


	def handleIncomingMessage(self, message: messages.AnyMessage) -> None:
		#Process a single incoming message:
		log('<== ' + str(message))
		self.messageRouter.handleMessage(message)


	def handleOutgoingMessage(self, message: messages.AnyMessage) -> None:
		#Process a single outgoing message:
		log('==> ' + str(message))
		self.messageRouter.handleMessage(message)



def terminateSignalHandler() -> None:
	loop = asyncio.get_event_loop() #type: asyncio.AbstractEventLoop
	loop.stop()


def main():
	client = BL4PClient() #type: BL4PClient
	loop = asyncio.get_event_loop() #type: asyncio.AbstractEventLoop

	loop.run_until_complete(client.startup())

	loop.add_signal_handler(signal.SIGINT , terminateSignalHandler)
	loop.add_signal_handler(signal.SIGTERM, terminateSignalHandler)
	loop.run_forever()

	loop.run_until_complete(client.shutdown())
	loop.close()



if __name__ == "__main__":
	main() #pragma: nocover

