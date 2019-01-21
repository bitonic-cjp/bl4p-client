class Transaction:
	def __init__(self, localOrderID, counterOffer):
		self.localOrderID = localOrderID
		self.counterOffer = counterOffer



class BuyTransaction(Transaction):
	def __init__(self, localOrderID, counterOffer):
		Transaction.__init__(self, localOrderID, counterOffer)
		print('Created buy tx')



class SellTransaction(Transaction):
	def __init__(self, localOrderID, counterOffer):
		Transaction.__init__(self, localOrderID, counterOffer)
		print('Created sell tx')

