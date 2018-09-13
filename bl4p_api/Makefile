.PHONY: proto

proto: bl4p.proto offer.proto
	protoc --python_out=. bl4p.proto offer.proto

	# Fix generated imports
	#See https://github.com/protocolbuffers/protobuf/issues/1491
	sed -i 's/^import \([^ ]*\)_pb2 as \([^ ]*\)$$/from . import \1_pb2 as \2/' *_pb2.py

