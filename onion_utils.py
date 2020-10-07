#    Copyright (C) 2020 by Bitonic B.V.
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

import struct
from typing import Any, Dict, List, Tuple

from log import log, logException



#ASCII-encoded "BL4P"
BL4P_TLV_TYPE = 0x424C3450 #type: int



def serializeBigsize(n: int) -> bytes:
	if n < 0xfd:
		return struct.pack('B', n)
	elif n < 0x10000:
		return b'\xfd' + struct.pack('>H', n)
	elif n < 0x100000000:
		return b'\xfe' + struct.pack('>I', n)
	else:
		return b'\xff' + struct.pack('>Q', n)


def deserializeBigsize(data: bytes) -> Tuple[int, bytes]:
	first = data[0] #type: int
	data = data[1:]
	if first == 0xff:
		return struct.unpack('>Q', data[:8])[0], data[8:]
	elif first == 0xfe:
		return struct.unpack('>I', data[:4])[0], data[4:]
	elif first == 0xfd:
		return struct.unpack('>H', data[:2])[0], data[2:]
	else:
		return first, data


def serializeTruncatedInt(fmt: str, value: int) -> bytes:
	data = struct.pack(fmt, value) #type: bytes
	while data and data[0] == 0:
		data = data[1:]
	return data


def serializeTLVPayload(TLVData: Dict[int, bytes]) -> bytes:
	keys = list(TLVData.keys()) #type: List[int]
	keys.sort()
	hop_payload = b'' #type: bytes
	for k in keys:
		T = serializeBigsize(k) #type: bytes
		V = TLVData[k] #type: bytes
		L = serializeBigsize(len(V)) #type: bytes
		hop_payload += T + L + V
	hop_payload_length = serializeBigsize(len(hop_payload)) #type: bytes
	return hop_payload_length + hop_payload


def deserializeTLVPayload(TLVData: bytes) -> Dict[int, bytes]:
	hop_payload_length, data = deserializeBigsize(TLVData) #type: Tuple[int, bytes]
	assert hop_payload_length != 0
	assert hop_payload_length == len(data)
	ret = {} #type: Dict[int, bytes]
	while data:
		T = -1 #type: int
		L = -1 #type: int
		T, data = deserializeBigsize(data)
		L, data = deserializeBigsize(data)
		assert L <= len(data)
		V = data[:L] #type: bytes
		data = data[L:]
		ret[T] = V
	return ret


def serializeStandardPayload(route_data: Dict[str, Any], blockHeight: int) -> bytes:
	style = route_data['style'] #type: str
	if style == 'legacy':
		realm = b'\x00' #type: bytes
		#This may be Bitcoin-specific:
		# Short Channel ID is composed of 3 bytes for the block height, 3
		# bytes of tx index in block and 2 bytes of output index
		chnBlockHeightStr, chnTxIndexStr, chnOutputIndexStr = \
			route_data['channel'].split('x') #type: Tuple[str, str, str]
		chnBlockHeight = struct.pack('>I', int(chnBlockHeightStr))[-3:] #type: bytes
		chnTxIndex = struct.pack('>I', int(chnTxIndexStr))[-3:] #type: bytes
		chnOutputIndex = struct.pack('>H', int(chnOutputIndexStr)) #type: bytes
		short_channel_id = chnBlockHeight + chnTxIndex + chnOutputIndex #type: bytes

		amt_to_forward = route_data['msatoshi'] #type: int
		outgoing_cltv_value = blockHeight + route_data['delay'] #type: int
		return \
			realm + struct.pack('>8sQI',
				short_channel_id,
				amt_to_forward,
				outgoing_cltv_value
				) + 24*b'\0'
	elif style == 'tlv':
		#This may be Bitcoin-specific:
		# Short Channel ID is composed of 3 bytes for the block height, 3
		# bytes of tx index in block and 2 bytes of output index
		chnBlockHeightStr, chnTxIndexStr, chnOutputIndexStr = \
			route_data['channel'].split('x')
		chnBlockHeight = struct.pack('>I', int(chnBlockHeightStr))[-3:]
		chnTxIndex = struct.pack('>I', int(chnTxIndexStr))[-3:]
		chnOutputIndex = struct.pack('>H', int(chnOutputIndexStr))
		short_channel_id = chnBlockHeight + chnTxIndex + chnOutputIndex

		amt_to_forward = route_data['msatoshi']
		outgoing_cltv_value = blockHeight + route_data['delay']
		return serializeTLVPayload({
			2: serializeTruncatedInt('>Q', amt_to_forward),
			4: serializeTruncatedInt('>I', outgoing_cltv_value),
			6: short_channel_id,
			})

	log('Got unrecognized route data: ' + str(route_data))
	raise Exception('Style not supported: ' + style)


def makeCreateOnionHopsData(
	route: List[Dict[str, Any]],
	customData: bytes,
	blockHeight: int
	) -> List[Dict[str, Any]]:

	payloads = [serializeStandardPayload(hop, blockHeight) for hop in route[1:]] #type: List[bytes]
	customPayload = serializeTLVPayload({BL4P_TLV_TYPE: customData}) #type: bytes
	payloads.append(customPayload)

	return \
	[
	{'pubkey': r['id'], 'payload': pl.hex()}
	for r, pl in zip(route, payloads)
	]


def readCustomPayloadData(payload: bytes) -> bytes:
	try:
		TLVData = deserializeTLVPayload(payload) #type: Dict[int, bytes]
	except:
		log('Exception when trying to deserialize the onion payload:')
		logException()
		raise

	if list(TLVData.keys()) != [BL4P_TLV_TYPE]:
		log('Received an incoming transaction with unrecognized payload format')
		raise Exception('Not our onion data format')
	return TLVData[BL4P_TLV_TYPE]

