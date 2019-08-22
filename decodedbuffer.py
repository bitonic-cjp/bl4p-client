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

class DecodedBuffer:
	'''
	A buffer for a byte stream that is to interpreted as a character stream.

	With the append() method, you can append bytes.
	These typically originate from something like a recv() on a network
	socket.

	With the get() method, you can look at the decoded characters (str) that
	are in the buffer.

	With the set() method, you can replace the buffer contents.
	This is typically done to remove parsed characters, e.g.
	buffer.set(buffer.get()[length:])

	The implementation assumes that all character boundaries are also byte
	boundaries.
	'''

	def __init__(self, encoding) -> None:
		self.encoding = encoding #type: str
		self.decoded = '' #type: str
		self.remainder = b'' #type: bytes


	def append(self, b: bytes) -> None:
		'Append bytes from b to the buffer.'

		self.remainder += b
		for i in range(len(b)):
			pos = len(self.remainder) - i #type: int
			firstPart = self.remainder[:pos] #type: bytes
			try:
				self.decoded += firstPart.decode(self.encoding)
				self.remainder = self.remainder[pos:]
				break
			except:
				continue


	def get(self) -> str:
		'Get the character contents of the buffer.'

		return self.decoded


	def set(self, s: str) -> None:
		'Replace the character buffer with s.'

		self.decoded = s



def main(): #pragma: nocover
	b = DecodedBuffer('UTF-8')
	b.append(b'Corn\xc3')
	print(b.get())
	print(b.remainder)
	b.set(b.get()[3:])
	print(b.get())
	print(b.remainder)
	b.append(b'\xa9 Plooy')
	print(b.get())
	print(b.remainder)
	b.set(b.get()[3:])
	print(b.get())
	print(b.remainder)



if __name__ == "__main__":
	main() #pragma: nocover

