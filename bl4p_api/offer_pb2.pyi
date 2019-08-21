class Offer:
	class Condition:
		pass

	#Actually this should be in a common base class of all message classes,
	#but for now it seems it is only used in Offer
	def CopyFrom(self, other: Offer) -> None:
		pass

