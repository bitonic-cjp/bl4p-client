from typing import Iterable

from .offer_pb2 import Offer



Msg_Error                 = ... #type: int

Msg_BL4P_Start            = ... #type: int
Msg_BL4P_StartResult      = ... #type: int
Msg_BL4P_SelfReport       = ... #type: int
Msg_BL4P_SelfReportResult = ... #type: int
Msg_BL4P_CancelStart      = ... #type: int
Msg_BL4P_CancelStartResult= ... #type: int
Msg_BL4P_Send             = ... #type: int
Msg_BL4P_SendResult       = ... #type: int
Msg_BL4P_Receive          = ... #type: int
Msg_BL4P_ReceiveResult    = ... #type: int
Msg_BL4P_GetStatus        = ... #type: int
Msg_BL4P_GetStatusResult  = ... #type: int

Msg_BL4P_AddOffer         = ... #type: int
Msg_BL4P_AddOfferResult   = ... #type: int
Msg_BL4P_ListOffers       = ... #type: int
Msg_BL4P_ListOffersResult = ... #type: int
Msg_BL4P_RemoveOffer      = ... #type: int
Msg_BL4P_RemoveOfferResult= ... #type: int
Msg_BL4P_FindOffers       = ... #type: int
Msg_BL4P_FindOffersResult = ... #type: int


class BL4P_Amount:
	amount = 0 #type: int

class BL4P_CryptoData:
	data = b'' #type: bytes

class Error:
	request = 0 #type: int
	reason  = 0 #type: int

class BL4P_Start:
	amount                  = None  #type: BL4P_Amount
	sender_timeout_delta_ms = 0     #type: int
	locked_timeout_delta_s  = 0     #type: int
	receiver_pays_fee       = False #type: bool

class BL4P_StartResult:
	request         = 0    #type: int
	sender_amount   = None #type: BL4P_Amount
	receiver_amount = None #type: BL4P_Amount
	payment_hash    = None #type: BL4P_CryptoData


class BL4P_SelfReportContents:
	class pair:
		name  = '' #type: str
		value = '' #type: str

	class PairList(Iterable[BL4P_SelfReportContents.pair]):
		def add(self) -> BL4P_SelfReportContents.pair:
			pass

	items = None #type: PairList

	def ParseFromString(self, s: bytes) -> None:
		pass

	def SerializeToString(self) -> bytes:
		pass

class BL4P_SelfReport:
	report    = b'' #type: bytes
	signature = b'' #type: bytes

class BL4P_SelfReportResult:
	pass

class BL4P_CancelStart:
	payment_hash = None #type: BL4P_CryptoData

class BL4P_CancelStartResult:
	pass

class BL4P_Send:
	sender_amount              = None #type: BL4P_Amount
	payment_hash               = None #type: BL4P_CryptoData
	max_locked_timeout_delta_s = 0    #type: int

	report                     = b'' #type: bytes
	signature                  = b'' #type: bytes

class BL4P_SendResult:
	request          = 0    #type: int
	payment_preimage = None #type: BL4P_CryptoData

class BL4P_Receive:
	payment_preimage = None #type: BL4P_CryptoData

class BL4P_ReceiveResult:
	pass

class BL4P_GetStatus:
	pass

class BL4P_GetStatusResult:
	pass

class BL4P_AddOffer:
	offer = None #type: Offer

class BL4P_AddOfferResult:
	request = 0 #type: int
	offerID = 0 #type: int

class BL4P_ListOffers:
	pass

class BL4P_ListOffersResult:
	class Item:
		offerID = 0    #type: int
		offer   = None #type: Offer
	offers = None #type: Iterable[Item]

class BL4P_RemoveOffer:
	offerID = 0 #type: int

class BL4P_RemoveOfferResult:
	pass

class BL4P_FindOffers:
	query = None #type: Offer

class BL4P_FindOffersResult:
	request = 0    #type: int
	offers  = None #type: Iterable[Offer]

