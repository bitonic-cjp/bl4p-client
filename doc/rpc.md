# BL4P plugin RPC calls

## bl4p.getfiatcurrency

### Input:

(None)

### Output:

* **name** (str):
  The name of the currency.
* **divisor** (int): 
  The division factor of the common unit of the currency into its fundamental
  integer units.
  For instance, for Bitcoin, subdivided into msatoshi units (11 decimal places),
  this is 100000000000.

### Description:

Returns information on the fiat currency being handled by the plugin.

### Errors:

(None)


## bl4p.getcryptocurrency

### Input:

(None)

### Output:

* **name** (str):
  The name of the currency.
* **divisor** (int): 
  The division factor of the common unit of the currency into its fundamental
  integer units.
  For instance, for Bitcoin, subdivided into msatoshi units (11 decimal places),
  this is 100000000000.

### Description:

Returns information on the cryptocurrency being handled by the plugin.

### Errors:

(None)


## bl4p.buy

### Input:

* **limit_rate** (int):
  The limit rate of the order, expressed in fundamental units of the fiat
  currency per common unit of the cryptocurrency.
  So, for instance, for trading BTC against EUR, if EUR has a divisor of
  10000 (5 decimal places), then a limit rate of 12 EUR/BTC is given as an
  argument value of 120000.
* **amount** (int):
  The maximum fiat amount to be spent in buying, expressed in fundamental units
  of the fiat currency.
  So, for instance, if EUR has a divisor of 10000 (5 decimal places), then an
  amount of 12 EUR is given as an argument value of 12000.

### Output:

(None)

### Description:

Adds a buy order.

### Errors:

TBD: what if limit_rate or amount is not int


## bl4p.sell

### Input:

* **limit_rate** (int):
  The limit rate of the order, expressed in fundamental units of the fiat
  currency per common unit of the cryptocurrency.
  So, for instance, for trading BTC against EUR, if EUR has a divisor of
  10000 (5 decimal places), then a limit rate of 12 EUR/BTC is given as an
  argument value of 120000.
* **amount** (int):
  The maximum crypto amount to be sold, expressed in fundamental units
  of the cryptocurrency.
  So, for instance, if BTC has a divisor of 100000000000 (11 decimal places),
  then an amount of 12 BTC is given as an argument value of 1200000000000.

### Output:

(None)

### Description:

Adds a sell order.

### Errors:

TBD: what if limit_rate or amount is not int


## bl4p.list

### Input:

(None)

### Output:

* **sell** (list of dict of str -> any):
* **buy** (list of dict of str -> any):

Each element of buy and sell contains the following elements:

* **limitRate** (int):
  The limitRate as given in the buy/sell command.
* **amount** (int):
  The amount as given in the buy/sell command.

### Description:

Returns a list of all orders.

### Errors:

(None)


## bl4p.setconfig

### Input:

* **values** (dict of str -> str):
  key: value pairs of all configuration values that need to be set.

### Output:

(None)

### Description:

Sets BL4P configuration values.
Currently supported configuration keys are:

* **bl4p.url**: 
  The websocket URL of the BL4P server.
* **bl4p.apiKey**: 
  The API key for the BL4P server connection.
* **bl4p.apiSecret**: 
  The base64-encoded secret for the BL4P server connection.
* **bl4p.signingPrivateKey**: 
  The hex-encoded private key used for signing self-reporting information that
  is sent to the BL4P server.

### Errors:

TBD: what if keys are not valid setting names

