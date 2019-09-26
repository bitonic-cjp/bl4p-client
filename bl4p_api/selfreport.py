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

from . import bl4p_pb2



def deserialize(b):
	pb2 = bl4p_pb2.BL4P_SelfReportContents()
	pb2.ParseFromString(b)
	ret = {}
	for item in pb2.items:
		ret[item.name] = item.value
	return ret


def serialize(d):
	pb2 = bl4p_pb2.BL4P_SelfReportContents()
	for k,v in d.items():
		item = pb2.items.add()
		item.name = k
		item.value = v
	return pb2.SerializeToString()

