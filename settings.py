#!/usr/bin/env python3
#    Copyright (C) 2019-2021 by Bitonic B.V.
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

from bl4p_api import offer



cryptoName    = 'btc'        #type: str
cryptoDivisor = 100000000000 #type: int #in mSatoshi

fiatName    = 'eur'  #type: str
fiatDivisor = 100000 #type: int         #in mCent

#We require a minimum CLTV time for incoming crypto funds
buyOrderCLTVExpiryDeltaRange  = (12     , offer.CONDITION_NO_MAX)
#We require a maximum sender timeout for outgoing fiat funds
buyOrderSenderTimeoutRange    = (10000  , 30000                 ) #milliseconds
#We require a maximum lock timeout for outgoing fiat funds
buyOrderLockedTimeoutRange    = (0      , 3600*24*14            ) #seconds

#We require a maximum CLTV time for outgoing crypto funds
sellOrderCLTVExpiryDeltaRange = (0      , 144                   )
#We require a maximum sender timeout for incoming fiat funds
sellOrderSenderTimeoutRange   = (2000   , 10000                 ) #milliseconds
#We require a minimum lock timeout for incoming fiat funds
sellOrderLockedTimeoutRange   = (3600*24, offer.CONDITION_NO_MAX) #seconds

#Maximum Lightning fee percentage.
#The amount of BTC lost in a sell transaction may exceed the limit of an order
#by this much.
maxLightningFee = 0.01

