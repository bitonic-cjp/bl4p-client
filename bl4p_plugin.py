#!/usr/bin/env python3
#    Copyright (C) 2019-2021 by Bitonic B.V.
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
import logging
import os
import signal
import sys
from typing import Optional, Tuple

import secp256k1

import backend
import bl4p_interface
import messages
import plugin_interface
import rpc_interface



async_stdio = None #type: Optional[Tuple[asyncio.StreamReader, asyncio.streams.StreamWriter]]
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
		self.bl4pConnectedFuture = asyncio.Future() #type: asyncio.Future
		self.shutdownFuture = asyncio.Future() #type: asyncio.Future


	async def startup(self) -> None:
		#The startup sequence is quite complex, with all kinds of
		#inter-dependencies between subsystems.

		#The first thing we can do is create the plugin interface
		#(based on the stdio streams), and perform its startup sequence.
		#This will give us the values of various (commandline) parameters
		#passed to lightningd.
		stdin, stdout = await stdio() #type: Tuple[asyncio.StreamReader, asyncio.streams.StreamWriter]
		self.pluginInterface = plugin_interface.PluginInterface(self, stdin, stdout) #type: plugin_interface.PluginInterface
		await self.pluginInterface.startup() #Guarantees that init is called

		#The log filename is a commandline parameter.
		#Now that we know it, we can start logging to it:
		logging.basicConfig(
			filename=self.pluginInterface.logFile,
			format = '%(asctime)s %(levelname)s: %(message)s',
			level = logging.INFO,
			)
		logging.info('\n\n\n\nOpened the log file')

		#The plugin interface start-up also informed us about the lightningd
		#RPC path.
		#Using this, we can create the RPC interface and start it up.
		#This will give us our Lightning node ID.
		reader, writer = await asyncio.open_unix_connection(path=self.pluginInterface.RPCPath) #type: ignore #mypy bug: it doesn't know open_unix_connection
		self.rpcInterface = rpc_interface.RPCInterface(self, reader, writer) #type: rpc_interface.RPCInterface
		await self.rpcInterface.startupRPC()

		#We can create the BL4P interface, but we cannot start it yet.
		#Creating it doesn't really do anything and doesn't depend on anything.
		self.bl4pInterface = bl4p_interface.BL4PInterface(self) #type: bl4p_interface.BL4PInterface

		#We can inform the backend about certain information.
		self.backend.setLNAddress(self.rpcInterface.nodeID)
		#TODO (bug 16): get address from BL4P
		self.backend.setBL4PAddress('BL4Pdummy')

		#The DB file is a commandline parameter.
		#Now that we know it and we passed the other information to the backend,
		#we can start up the backend.
		#This will load data from the DB file (like the configuration),
		#and start certain tasks.
		self.backend.startup(self.pluginInterface.DBFile)

		#The subsystems that have been started can be added as message handlers.
		self.messageRouter.addHandler(self.backend)
		self.messageRouter.addHandler(self.pluginInterface)
		self.messageRouter.addHandler(self.rpcInterface)

		#We can now start up the BL4P interface.
		#This depends on configuration data from the backend.
		await self.startupBL4PInterface()

		#Only start messaging at the very end
		logging.info('Startup has finished; we can now start messaging.')
		self.messageRouter.startMessaging()


	async def startupBL4PInterface(self) -> None:
		conf = self.backend.configuration

		#We try to startup the BL4P interface, using config settings from the
		#backend.
		try:
			await self.bl4pInterface.startupInterface(
				conf.getValue('bl4p.url'),
				conf.getValue('bl4p.apiKey'),
				conf.getValue('bl4p.apiSecret'),
				secp256k1.PrivateKey(privkey=bytes.fromhex(
					conf.getValue('bl4p.signingPrivateKey')
					)),
				)
		except:
			#TODO (bug 20): handle BL4P server connection issues (e.g. notify user)
			logging.exception('Exception when starting BL4P interface:')
			logging.error('Due to the above exception, we continue without connection to BL4P')
			return

		#If startup was successful, we can add this interface as a message handler.
		self.messageRouter.addHandler(self.bl4pInterface)
		self.bl4pConnectedFuture.set_result(True)


	async def shutdown(self) -> None:
		logging.info('Shutting down backend')
		await self.backend.shutdown()
		logging.info('Shutting down BL4P interface')
		await self.bl4pInterface.shutdown()
		logging.info('Shutting down RPC interface')
		await self.rpcInterface.shutdown()
		logging.info('Shutting down plugin interface')
		await self.pluginInterface.shutdown()
		logging.info('Shutting down is complete')
		self.shutdownFuture.set_result(True)


	def isBL4PConnected(self) -> bool:
		return self.bl4pConnectedFuture.done()


	async def waitForBL4PConnection(self) -> None:
		await self.bl4pConnectedFuture


	def handleIncomingMessage(self, message: messages.AnyMessage) -> None:
		#Process a single incoming message:
		logging.info('<== ' + str(message))
		self.messageRouter.handleMessage(message)


	def handleOutgoingMessage(self, message: messages.AnyMessage) -> None:
		#Process a single outgoing message:
		logging.info('==> ' + str(message))
		self.messageRouter.handleMessage(message)



def main():
	client = BL4PClient() #type: BL4PClient
	loop = asyncio.get_event_loop() #type: asyncio.AbstractEventLoop

	loop.run_until_complete(client.startup())

	def terminateSignalHandler() -> None:
		#Run shutdown in a new task:
		asyncio.ensure_future(client.shutdown())

	loop.add_signal_handler(signal.SIGINT , terminateSignalHandler)
	loop.add_signal_handler(signal.SIGTERM, terminateSignalHandler)
	loop.run_until_complete(client.shutdownFuture)

	loop.close()



if __name__ == "__main__":
	main() #pragma: nocover

