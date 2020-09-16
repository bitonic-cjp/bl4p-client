from typing import Iterable, Iterator



class Offer:
	class Asset:
		max_amount = 0 #type: int
		max_amount_divisor = 0 #type: int
		currency = '' #type: str
		exchange = '' #type: str

		def CopyFrom(self, other: Offer.Asset) -> None:
			pass

	class Condition:
		CLTV_EXPIRY_DELTA = 1 #type: int
		SENDER_TIMEOUT    = 2 #type: int
		LOCKED_TIMEOUT    = 3 #type: int

		key = 0 #type: int
		min_value = 0 #type: int
		max_value = 0 #type: int

	class ConditionList(Iterable[Offer.Condition]):
		def add(self) -> Offer.Condition:
			pass

		def __iter__(self) -> Iterator[Offer.Condition]:
			pass


	bid = Asset() #type: Asset
	ask = Asset() #type: Asset
	address = '' #type: str
	ID = 0 #type: int
	conditions = None #type: ConditionList

	#Actually this should be in a common base class of all message classes,
	#but for now it seems it is only used in Offer
	def CopyFrom(self, other: Offer) -> None:
		pass

	def ParseFromString(self, s: bytes) -> None:
		pass


	def SerializeToString(self) -> bytes:
		pass

