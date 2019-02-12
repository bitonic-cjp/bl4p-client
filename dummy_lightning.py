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
import socket
import time
import traceback



class Node:
	def __init__(self, nodeID, RPCFile):
		self.nodeID = nodeID
		self.RPCFile = RPCFile


	async def startup(self):
		try:
			os.remove(self.RPCFile)
		except FileNotFoundError:
			pass #it's ok
		self.rpc = await asyncio.start_unix_server(
			client_connected_cb=self.RPCConnection,
			path=self.RPCFile
			)

		self.plugin = await asyncio.create_subprocess_exec(
			'./bl4p_plugin.py',
			stdin=asyncio.subprocess.PIPE,
			stdout=asyncio.subprocess.PIPE,
			stderr=None, #Inherited
			)


	async def RPCConnection(self, reader, writer):
		try:
			print('Lightning: Got incoming RPC connection')
			while True:
				line = await reader.readline()
				if line == b'': #EOF
					break

				if b'"id"' in line:
					print('Lightning: Got RPC command ', line)
					command = line.strip()
					pluginResponse = await self.pluginRPC(command)
					print('Lightning: Got plugin response ', pluginResponse)
				else:
					print('Lightning: Got RPC notification ', line)
					command = line.strip()
					await self.pluginNotify(command)

		except:
			print(traceback.format_exc())

		print('Lightning: Ended RPC connection')


	async def pluginRPC(self, command):
		self.plugin.stdin.write(b'%s\n\n' % command)
		await self.plugin.stdin.drain()
		ret = await self.plugin.stdout.readline()
		c = await self.plugin.stdout.read(1)
		assert c == b'\n'
		return ret


	async def pluginNotify(self, command):
		self.plugin.stdin.write(b'%s\n\n' % command)
		await self.plugin.stdin.drain()


	async def shutdown(self):
		self.plugin.kill()
		await self.plugin.wait()



nodes = \
[
	Node(nodeID='node0', RPCFile='node0-rpc'),
	Node(nodeID='node1', RPCFile='node1-rpc'),
]



async def startup():
	print('Starting nodes')
	for n in nodes:
		await n.startup()


async def shutdown():
	print('Shutting down nodes')
	for n in nodes:
		await n.shutdown()


def terminateSignalHandler():
	print('Got signal to terminate')
	loop = asyncio.get_event_loop()
	loop.stop()


loop = asyncio.get_event_loop()

loop.run_until_complete(startup())

loop.add_signal_handler(signal.SIGINT , terminateSignalHandler)
loop.add_signal_handler(signal.SIGTERM, terminateSignalHandler)
loop.run_forever()

loop.run_until_complete(shutdown())
loop.close()

