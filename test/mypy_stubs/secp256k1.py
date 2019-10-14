class Signature:
	pass


class PrivateKey:
	def __init__(self, privkey: bytes) -> None:
		pass

	def ecdsa_sign(self, msg: bytes) -> Signature:
		pass

	def ecdsa_serialize(self, sig: Signature) -> bytes:
		pass

