#!/usr/bin/env python3
#    Copyright (C) 2019-2020 by Bitonic B.V.
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
from enum import Enum
import inspect
import os
import re
from typing import Any, Callable, Dict, List, Optional, Tuple, Union, TYPE_CHECKING

if TYPE_CHECKING:
	import bl4p_plugin #pragma: nocover

from json_rpc import JSONRPC
from ln_payload import Payload
from log import log, logException
import messages
import onion_utils
import settings



class MethodType(Enum):
    RPCMETHOD = 0 #type: int
    HOOK      = 1 #type: int



class OngoingRequest:
	#Which attributes are used depends on the call:
	paymentHash = None #type: bytes


NO_RESPONSE = object() #Placeholder in case no response is to be sent



class PluginInterface(JSONRPC, messages.Handler):
	def __init__(self, client: 'bl4p_plugin.BL4PClient', inputStream: asyncio.StreamReader, outputStream: asyncio.StreamWriter) -> None:
		JSONRPC.__init__(self, inputStream, outputStream)
		messages.Handler.__init__(self, {
			messages.LNFinish: self.sendFinish,
			messages.LNFail  : self.sendFail,

			messages.PluginCommandResult: self.sendPluginCommandResult,
			messages.PluginCommandError : self.sendPluginCommandError,
			})
		self.client = client #type: bl4p_plugin.BL4PClient

		self.options = \
		[
		{
		'name'       : 'bl4p.logfile',
		'default'    : 'bl4p.log',
		'description': 'BL4P plug-in log file',
		'type'       : 'string',
		},
		{
		'name'       : 'bl4p.dbfile',
		'default'    : 'bl4p.db',
		'description': 'BL4P plug-in database file',
		'type'       : 'string',
		},
		] #type: List[Dict[str, str]]
		self.methods = \
		{
		'getmanifest': (self.getManifest, MethodType.RPCMETHOD),
		'init'       : (self.init       , MethodType.RPCMETHOD),

		'bl4p.getfiatcurrency'  : (self.getFiatCurrency   , MethodType.RPCMETHOD),
		'bl4p.getcryptocurrency': (self.getCryptoCurrency , MethodType.RPCMETHOD),
		'bl4p.buy'              : (self.buy               , MethodType.RPCMETHOD),
		'bl4p.sell'             : (self.sell              , MethodType.RPCMETHOD),
		'bl4p.list'             : (self.list              , MethodType.RPCMETHOD),

		'htlc_accepted'         : (self.handleHTLCAccepted, MethodType.HOOK),
		} #type: Dict[str, Tuple[Callable, MethodType]]

		self.subscriptions = {} #type: Dict[str, Callable]

		self.currentRequestID = None #type: Optional[int]
		self.ongoingRequests = {} #type: Dict[int, Tuple[str, OngoingRequest]] #ID -> (methodname, OngoingRequest)


	async def startup(self):
		#Keep handling messages until one message handler sets self.RPCPath
		#(this happens on the init message)
		while not hasattr(self, 'RPCPath'):
			message = await self.getNextJSON() #type: Optional[Dict]
			if message is None:
				raise Exception('Plugin interface closed before init call')
			self.handleJSON(message)

		#Start the regular message handling thread
		return JSONRPC.startup(self)


	def handleRequest(self, ID: int, name: str, params: Dict) -> None:
		#We depend on C-Lightning to pass the expected types in params

		self.currentRequestID = ID
		try:
			func = self.methods[name][0] #type: Callable
			result = func(**params) #type: Any
			if result == NO_RESPONSE:
				return
			self.sendResponse(ID, result)
		except Exception as e:
			logException()
			self.sendErrorResponse(ID,
				1, #TODO: define error numbers
				"Error while processing {}: {}".format(
				name, repr(e)
				))
		self.currentRequestID = None


	def storeOngoingRequest(self, name: str, request: OngoingRequest) -> None:
		assert self.currentRequestID is not None
		self.ongoingRequests[self.currentRequestID] = name, request


	def findOngoingRequest(self, name: str, func: Callable) -> int:
		ID = -1 #type: int

		for ID, value in self.ongoingRequests.items():
			methodName, request = value #type: Tuple[str, OngoingRequest]
			if methodName == name and func(request):
				return ID
		raise IndexError()


	def sendOngoingRequestResponse(self, ID: int, result: Any) -> None:
		#TODO: have a way to send delayed error responses
		del self.ongoingRequests[ID]
		self.sendResponse(ID, result)


	def handleNotification(self, name: str, params: Dict) -> None:
		#We depend on C-Lightning to pass the expected types in params
		func = self.subscriptions[name]
		func(**params)


	def getManifest(self, **kwargs) -> Dict[str, Any]:
		name = '' #type: str

		methods = [] #type: List[Dict[str, str]]
		hooks = [] #type: List[str]
		for name, entry in self.methods.items():
			func, typ = entry #type: Tuple[Callable, MethodType]
			# Skip the builtin ones, they don't get reported
			if name in ['getmanifest', 'init']:
				continue

			if typ == MethodType.HOOK:
				hooks.append(name)
				continue

			doc = inspect.getdoc(func)
			if not doc:
				log(
				'RPC method \'{}\' does not have a docstring.'.format(name)
				)
				doc = "Undocumented RPC method from a plugin."
				doc = re.sub('\n+', ' ', doc)

			methods.append({
				'name': name,
				'description': doc,
				})

		return {
			'options': self.options,
			'rpcmethods': methods,
			'subscriptions': list(self.subscriptions.keys()),
			'hooks': hooks,
			}


	def init(self, options: Dict[str, str], configuration: Dict[str, str], **kwargs) -> None:
		#We depend on C-Lightning to pass the expected types in options, configuration

		#self.log('Plugin init got called')

		filename = configuration['rpc-file'] #type: str
		lndir = configuration['lightning-dir'] #type: str

		self.RPCPath = os.path.join(lndir, filename) #type: str
		self.logFile = options['bl4p.logfile'] #type: str
		self.DBFile = options['bl4p.dbfile'] #type: str
		#self.log('RPC path is ' + self.RPCPath)


	def getFiatCurrency(self) -> Dict[str, Any]:
		'Returns information about the fiat-currency'
		return {'name': settings.fiatName, 'divisor': settings.fiatDivisor}


	def getCryptoCurrency(self) -> Dict[str, Any]:
		'Returns information about the crypto-currency'
		return {'name': settings.cryptoName, 'divisor': settings.cryptoDivisor}


	def buy(self, limit_rate: int, amount: int, **kwargs) -> object:
		'Place an order for buying crypto-currency with fiat-currency'
		assert isinstance(limit_rate, int)
		assert isinstance(amount, int)

		self.client.handleIncomingMessage(messages.BuyCommand(
			commandID = self.currentRequestID,
			limitRate=limit_rate,
			amount=amount
			))

		#Don't send a response now:
		#It was already sent by the message handler
		return NO_RESPONSE


	def sell(self, limit_rate: int, amount: int, **kwargs) -> object:
		'Place an order for selling crypto-currency for fiat-currency'
		assert isinstance(limit_rate, int)
		assert isinstance(amount, int)

		self.client.handleIncomingMessage(messages.SellCommand(
			commandID = self.currentRequestID,
			limitRate=limit_rate,
			amount=amount
			))

		#Don't send a response now:
		#It was already sent by the message handler
		return NO_RESPONSE


	def list(self, **kwargs) -> object:
		'List active orders'

		self.client.handleIncomingMessage(messages.ListCommand(
			commandID = self.currentRequestID,
			))

		#Don't send a response now:
		#It was already sent by the message handler
		return NO_RESPONSE


	def handleHTLCAccepted(self, onion: Dict[str, Any], htlc: Dict[str, Any], **kwargs) -> Union[object, Dict[str, str]]:
		'''
		Parameter format:
		'onion':
			{
			'payload':
			},
		'htlc':
			{
			'amount': str,
			'cltv_expiry': int,
			'payment_hash': hex,
			}
		'''
		#We depend on C-Lightning to pass the expected types in onion, htlc

		onionPayload = bytes.fromhex(onion['payload']) #type: bytes
		try:
			payloadData = onion_utils.readCustomPayloadData(onionPayload) #type: bytes
		except:
			log('We failed to deserialize the payload data, so we won\'t handle this transaction:')
			logException()
			return {'result': 'continue'} #it's not handled by us

		try:
			paymentHash = bytes.fromhex(htlc['payment_hash']) #type: bytes
			payload = Payload.decode(payloadData) #type: Payload
			amount_str = htlc['amount'] #type: str
			assert amount_str.endswith('msat') #TODO: may be Bitcoin-specific
			amount_str = amount_str[:-4] #remove trailing 'msat'
			cryptoAmount = int(amount_str) #type: int
			CLTVExpiryDelta = htlc['cltv_expiry'] #type: int #TODO: check if this is a relative or absolute value. For now, relative is used everywhere.
		except:
			log('Refused incoming transaction because there is something wrong with it:')
			logException()
			return {'result': 'fail'}

		#We will have to send a response later, possibly after finishing this function
		req = OngoingRequest() #type: OngoingRequest
		req.paymentHash = paymentHash
		self.storeOngoingRequest('htlc_accepted', req)

		self.client.handleIncomingMessage(messages.LNIncoming(
			paymentHash = paymentHash,
			cryptoAmount = cryptoAmount,
			CLTVExpiryDelta = CLTVExpiryDelta,
			fiatAmount = payload.fiatAmount,
			offerID = payload.offerID,
			))

		#Don't send a response now:
		#either it was already sent by the LNIncoming handler,
		#or we will send it later.
		return NO_RESPONSE


	def sendFinish(self, message: messages.LNFinish) -> None:
		try:
			ID = self.findOngoingRequest('htlc_accepted',
				lambda x: x.paymentHash == message.paymentHash) #type: int
		except IndexError:
			log('Cannot finish the Lightning transaction right now, because lightningd didn\'t give it to us.')
			log('This may be caused by a restart during an ongoing transaction.')
			log('Now we have to wait until lightningd gives it to us again.')
			return

		self.sendOngoingRequestResponse(ID, {
			'result': 'resolve',
			'payment_key': message.paymentPreimage.hex(),
			})


	def sendFail(self, message: messages.LNFail) -> None:
		try:
			ID = self.findOngoingRequest('htlc_accepted',
				lambda x: x.paymentHash == message.paymentHash) #type: int
		except IndexError:
			log('Cannot fail the Lightning transaction right now, because lightningd didn\'t give it to us.')
			log('This may be caused by a restart during an ongoing transaction.')
			log('Now we have to wait until lightningd gives it to us again.')
			return

		self.sendOngoingRequestResponse(ID, {
			'result': 'fail',
			})


	def sendPluginCommandResult(self, message: messages.PluginCommandResult) -> None:
		self.sendResponse(message.commandID,
			message.result)


	def sendPluginCommandError(self, message: messages.PluginCommandError) -> None:
		self.sendErrorResponse(message.commandID,
			message.code, message.message)

