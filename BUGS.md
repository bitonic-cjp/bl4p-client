# Bugs
This document lists known bugs.
They are sorted by their (security) impact.

Please keep in mind that BL4P is experimental and unfinished software.
There are probably lots of bugs that do exist even if they are not listed here.
The main purpose of this list is to act as a reminder for developers on what
has to be fixed.


## Execution of arbitrary code

(No known bugs in this category)


## Loss of funds (including trading beyond limits specified in orders)

### 1. Offers returned by BL4P are not checked
Although the BL4P server should only return offers that match the search query,
clients can and should check this for themselves, before acting upon received
offers.

### 2. BL4P fee amount is not checked
Although the BL4P server should never require excessive fees,
clients can and should check this for themselves, before executing transactions.


### 3. Re-notification of incoming Lightning tx is not handled correctly
Often this will not be a problem, but in rare cases, the incoming transaction
might be ignored, even though we have already committed to the outgoing
transaction.
A result could be that the incoming transaction gets canceled after time-out,
even while the outgoing transaction is successful.


### 4. No check on ongoing outgoing Lightning transactions.
After a crash, a duplicate Lightning transaction might be sent out.


### 5. Incoming transactions are not checked
Others can exchange with us on arbitrary conditions and exchange rates.


### 6. No check on the outgoing Lightning transaction lock time
It should be less than the BL4P lock time.


## Sub-optimal trading (within limits specified in orders)

### 7. All orders are immediately active
This is not necessarily desired behavior: it might be preferred to first
execute the most preferred orders, before activating less preferred orders.

### 8. The first returned offer is used
Instead, offers should be sorted based on a certain attractiveness measure,
for instance their exchange rate.


## Denial of Service

### 9. Race condition between publishing buy order and receiving transactions
On a buy order, if a Lightning transaction is received before the
offer-publishing RPC call finishes, the plugin might terminate.


## Database storage growth

### 10. Counter-offers
Counter-offers are stored every time, even if the same offer already exists in
the database.

### 11. Transactions
Old transactions are never removed from the database.

### 12. Orders
Old orders are never removed from the database.


## Missing feature

### 13. Buyer-initiated trade is missing
Maybe this feature is kind of impossible anyway, and should be removed from the
protocol.


### 14. Fixed BL4P URL
In fact, it's currently hardcoded to be localhost.


### 15. Fixed BL4P acount name, password and private key
It's currently '3', '3' and SHA256('3').


### 16. Fixed BL4P address
It's currently 'BL4Pdummy'.
Might not matter anymore if buyer-initiated trade is removed.


### 18. No per-transaction maximum amount
Currently, it equals the remaining order amount.


## Future and unknown bugs

### 19. (This is the lowest non-assigned bug ID)

