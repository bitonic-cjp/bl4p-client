class Offer:
	class Condition:
		CLTV_EXPIRY_DELTA = 1 #type: int
		SENDER_TIMEOUT    = 2 #type: int
		LOCKED_TIMEOUT    = 3 #type: int

	#Actually this should be in a common base class of all message classes,
	#but for now it seems it is only used in Offer
	def CopyFrom(self, other: Offer) -> None:
		pass

	def ParseFromString(self, s: bytes) -> None:
		pass

