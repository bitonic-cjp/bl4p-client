#    Copyright (C) 2019-2020 by Bitonic B.V.
#
#    This file is part of BL4P Client.
#
#    BL4P Client is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    BL4P Client is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with BL4P Client. If not, see <http://www.gnu.org/licenses/>.

.PHONY: all test typetest unittest

all: test

test: typetest unittest

current_dir = $(shell pwd)

#Depends on mypy version:
MYPY_OPTS =
#MYPY_OPTS = --fast-parser

typetest:
	cd .. && MYPYPATH=$(current_dir)/mypy_stubs mypy $(MYPY_OPTS) bl4p_plugin.py

unittest:
	-rm -rf coverage-html
	-rm -rf .coverage
	python3-coverage erase
	python3-coverage run -p test_backend.py
	python3-coverage run -p test_bl4p_interface.py
	python3-coverage run -p test_bl4p_plugin.py
	python3-coverage run -p test_decodedbuffer.py
	python3-coverage run -p test_json_rpc.py
	python3-coverage run -p test_ln_payload.py
	python3-coverage run -p test_log.py
	python3-coverage run -p test_messages.py
	python3-coverage run -p test_order.py
	python3-coverage run -p test_ordertask.py
	python3-coverage run -p test_plugin_interface.py
	python3-coverage run -p test_rpc_interface.py
	python3-coverage run -p test_storage.py
	python3-coverage run -p test_simplestruct.py
	python3-coverage combine
	python3-coverage html
	python3-coverage report

