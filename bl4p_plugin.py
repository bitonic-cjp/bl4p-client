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
import sys

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


pluginInterface = plugin_interface.PluginInterface()

async def main():
	stdin, stdout = await stdio()
	pluginInterface.startup(stdin, stdout)
	await pluginInterface.run()



asyncio.get_event_loop().run_until_complete(main())

