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

from bl4p_api import bl4p_pb2
from bl4p_api import asynclient as bl4p
from log import log
import messages



class BL4PInterface(bl4p.Bl4pApi):
	def handleResult(self, result):
		log('BL4PInterface: Received result: ' + str(result))
		#TODO
	def __init__(self, client):
		bl4p.Bl4pApi.__init__(self, log=log)
		self.client = client


	def sendOutgoingMessage(self, message):
		if isinstance(message, messages.BL4PAddOffer):
			request = bl4p_pb2.BL4P_AddOffer()
			request.offer.CopyFrom(message.offer.toPB2())
		else:
			raise Exception('BL4PInterface cannot send message ' + str(message))
		log('BL4PInterface: Sending request: ' + str(request))
		self.sendRequest(request)

