# bl4p-client
A client for the BL4P decentralized exchange.

## Dependencies

### For actual usage:

* C-Lightning. In fact, at the time of writing, bl4p-client has not been tested
yet with any C-Lightning version, so it is not yet known to work outside of
simulated environments.

### For actual usage, simulated usage or development and testing:

* Python 3, version 3.5 or later.
* Python3-protobuf
* Python3-websockets
* Python3 secp256k1 (in Debian: pip3 install secp256k1)

### For development and testing:

* Make
* Protobuf-compiler
* Python3-coverage
* Mypy

## Usage

### Actual usage:

Note that this is not possible as long as there is no running BL4P server.
Currently, this client has the hard-coded expectation to find a BL4P server at
localhost.

* Make sure that bl4p_plugin.py is executable and can be found by lightningd
when lightningd is started.
* Make sure that the other source files of bl4p-client can be imported, by
placing them in a suitable directory, setting PYTHONPATH, whatever.
* Start lightningd with arguments `--plugin=bl4p_plugin.py --bl4p.logfile=<logfile> --bl4p.dbfile=<dbfile>`
* Start `bl4p_console.py <lightningd-rpcfile>`

For further instructions, consult the help command in bl4p_console.py.

### Simulated usage:

Note that this is not possible as long as there is no running BL4P server.
Currently, this client has the hard-coded expectation to find a BL4P server at
localhost.

* Start `dummy_lightning.py`
* Start `bl4p_console.py node0-rpc` to have a console for one simulated node
* Start `bl4p_console.py node1-rpc` to have a console for another simulated node

For further instructions, consult the help command in bl4p_console.py.

### Unit tests

* Start `make test`

## Bugs
See BUGS.md

## Development
An overview of the source code is written in doc/Code overview.odp

