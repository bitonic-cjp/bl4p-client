from typing import Dict, Optional



class exceptions:
	class ConnectionClosed(Exception):
		pass



class WebSocketClientProtocol:
	async def recv(self) -> Optional[bytes]:
		pass

	async def send(self, data: bytes) -> None:
		pass

	async def close(self) -> None:
		pass



async def connect(uri: str) -> WebSocketClientProtocol:
	pass

