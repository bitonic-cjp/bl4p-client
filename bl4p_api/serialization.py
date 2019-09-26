#    Copyright (C) 2018 by Bitonic B.V.
#
#    This file is part of the BL4P API.
#
#    The BL4P API is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    The BL4P API is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with the BL4P API. If not, see <http://www.gnu.org/licenses/>.

import struct
from typing import Any, Dict, Type

from . import bl4p_pb2



id2type = \
{
bl4p_pb2.Msg_Error                 : bl4p_pb2.Error,

bl4p_pb2.Msg_BL4P_Start            : bl4p_pb2.BL4P_Start,
bl4p_pb2.Msg_BL4P_StartResult      : bl4p_pb2.BL4P_StartResult,
bl4p_pb2.Msg_BL4P_CancelStart      : bl4p_pb2.BL4P_CancelStart,
bl4p_pb2.Msg_BL4P_CancelStartResult: bl4p_pb2.BL4P_CancelStartResult,
bl4p_pb2.Msg_BL4P_Send             : bl4p_pb2.BL4P_Send,
bl4p_pb2.Msg_BL4P_SendResult       : bl4p_pb2.BL4P_SendResult,
bl4p_pb2.Msg_BL4P_Receive          : bl4p_pb2.BL4P_Receive,
bl4p_pb2.Msg_BL4P_ReceiveResult    : bl4p_pb2.BL4P_ReceiveResult,
bl4p_pb2.Msg_BL4P_GetStatus        : bl4p_pb2.BL4P_GetStatus,
bl4p_pb2.Msg_BL4P_GetStatusResult  : bl4p_pb2.BL4P_GetStatusResult,
bl4p_pb2.Msg_BL4P_SelfReport       : bl4p_pb2.BL4P_SelfReport,
bl4p_pb2.Msg_BL4P_SelfReportResult : bl4p_pb2.BL4P_SelfReportResult,

bl4p_pb2.Msg_BL4P_AddOffer          : bl4p_pb2.BL4P_AddOffer,
bl4p_pb2.Msg_BL4P_AddOfferResult    : bl4p_pb2.BL4P_AddOfferResult,
bl4p_pb2.Msg_BL4P_ListOffers        : bl4p_pb2.BL4P_ListOffers,
bl4p_pb2.Msg_BL4P_ListOffersResult  : bl4p_pb2.BL4P_ListOffersResult,
bl4p_pb2.Msg_BL4P_RemoveOffer       : bl4p_pb2.BL4P_RemoveOffer,
bl4p_pb2.Msg_BL4P_RemoveOfferResult : bl4p_pb2.BL4P_RemoveOfferResult,
bl4p_pb2.Msg_BL4P_FindOffers        : bl4p_pb2.BL4P_FindOffers,
bl4p_pb2.Msg_BL4P_FindOffersResult  : bl4p_pb2.BL4P_FindOffersResult,
} #type: Dict[int, Type]

type2id = {v:k for k,v in id2type.items()} #type: Dict[Type, int]



def serialize(obj: Any) -> bytes:
	typeID = type2id[obj.__class__] #type: int
	typeID_bytes = struct.pack('<I', typeID) #type: bytes #32-bit little endian
	serialized = obj.SerializeToString() #type: bytes
	return typeID_bytes + serialized


def deserialize(message: bytes) -> Any:
	typeID = struct.unpack('<I', message[:4])[0] #type: int #32-bit little endian
	serialized = message[4:] #type: bytes
	obj = id2type[typeID]() #type: Any
	obj.ParseFromString(serialized)
	return obj

