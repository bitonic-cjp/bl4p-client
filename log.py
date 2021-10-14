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

import logging



def setLogFile(filename: str) -> None:
	logging.basicConfig(
		filename=filename,
		format='%(asctime)s %(levelname)s: %(message)s',
		level=logging.INFO
		)
	log('\n\n\n\nOpened the log file')


def log(s: str) -> None:
	logging.info(s)


def logException() -> None:
	logging.exception('')

