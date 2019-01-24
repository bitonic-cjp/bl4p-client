# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: offer.proto

import sys
_b=sys.version_info[0]<3 and (lambda x:x) or (lambda x:x.encode('latin1'))
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
from google.protobuf import descriptor_pb2
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor.FileDescriptor(
  name='offer.proto',
  package='',
  syntax='proto3',
  serialized_pb=_b('\n\x0boffer.proto\"\xfb\x02\n\x05Offer\x12\x19\n\x03\x62id\x18\x01 \x01(\x0b\x32\x0c.Offer.Asset\x12\x19\n\x03\x61sk\x18\x02 \x01(\x0b\x32\x0c.Offer.Asset\x12\x0f\n\x07\x61\x64\x64ress\x18\x03 \x01(\t\x12$\n\nconditions\x18\x04 \x03(\x0b\x32\x10.Offer.Condition\x1a[\n\x05\x41sset\x12\x12\n\nmax_amount\x18\x01 \x01(\x04\x12\x1a\n\x12max_amount_divisor\x18\x02 \x01(\x04\x12\x10\n\x08\x63urrency\x18\x03 \x01(\t\x12\x10\n\x08\x65xchange\x18\x04 \x01(\t\x1a\xa7\x01\n\tCondition\x12!\n\x03key\x18\x01 \x01(\x0e\x32\x14.Offer.Condition.Key\x12\x11\n\tmin_value\x18\x02 \x01(\x12\x12\x11\n\tmax_value\x18\x03 \x01(\x12\"Q\n\x03Key\x12\x0b\n\x07UNKNOWN\x10\x00\x12\x15\n\x11\x43LTV_EXPIRY_DELTA\x10\x01\x12\x12\n\x0eSENDER_TIMEOUT\x10\x02\x12\x12\n\x0eLOCKED_TIMEOUT\x10\x03\x62\x06proto3')
)
_sym_db.RegisterFileDescriptor(DESCRIPTOR)



_OFFER_CONDITION_KEY = _descriptor.EnumDescriptor(
  name='Key',
  full_name='Offer.Condition.Key',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='UNKNOWN', index=0, number=0,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CLTV_EXPIRY_DELTA', index=1, number=1,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='SENDER_TIMEOUT', index=2, number=2,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='LOCKED_TIMEOUT', index=3, number=3,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=314,
  serialized_end=395,
)
_sym_db.RegisterEnumDescriptor(_OFFER_CONDITION_KEY)


_OFFER_ASSET = _descriptor.Descriptor(
  name='Asset',
  full_name='Offer.Asset',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='max_amount', full_name='Offer.Asset.max_amount', index=0,
      number=1, type=4, cpp_type=4, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='max_amount_divisor', full_name='Offer.Asset.max_amount_divisor', index=1,
      number=2, type=4, cpp_type=4, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='currency', full_name='Offer.Asset.currency', index=2,
      number=3, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='exchange', full_name='Offer.Asset.exchange', index=3,
      number=4, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=134,
  serialized_end=225,
)

_OFFER_CONDITION = _descriptor.Descriptor(
  name='Condition',
  full_name='Offer.Condition',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='key', full_name='Offer.Condition.key', index=0,
      number=1, type=14, cpp_type=8, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='min_value', full_name='Offer.Condition.min_value', index=1,
      number=2, type=18, cpp_type=2, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='max_value', full_name='Offer.Condition.max_value', index=2,
      number=3, type=18, cpp_type=2, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
    _OFFER_CONDITION_KEY,
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=228,
  serialized_end=395,
)

_OFFER = _descriptor.Descriptor(
  name='Offer',
  full_name='Offer',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='bid', full_name='Offer.bid', index=0,
      number=1, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='ask', full_name='Offer.ask', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='address', full_name='Offer.address', index=2,
      number=3, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='conditions', full_name='Offer.conditions', index=3,
      number=4, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[_OFFER_ASSET, _OFFER_CONDITION, ],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=16,
  serialized_end=395,
)

_OFFER_ASSET.containing_type = _OFFER
_OFFER_CONDITION.fields_by_name['key'].enum_type = _OFFER_CONDITION_KEY
_OFFER_CONDITION.containing_type = _OFFER
_OFFER_CONDITION_KEY.containing_type = _OFFER_CONDITION
_OFFER.fields_by_name['bid'].message_type = _OFFER_ASSET
_OFFER.fields_by_name['ask'].message_type = _OFFER_ASSET
_OFFER.fields_by_name['conditions'].message_type = _OFFER_CONDITION
DESCRIPTOR.message_types_by_name['Offer'] = _OFFER

Offer = _reflection.GeneratedProtocolMessageType('Offer', (_message.Message,), dict(

  Asset = _reflection.GeneratedProtocolMessageType('Asset', (_message.Message,), dict(
    DESCRIPTOR = _OFFER_ASSET,
    __module__ = 'offer_pb2'
    # @@protoc_insertion_point(class_scope:Offer.Asset)
    ))
  ,

  Condition = _reflection.GeneratedProtocolMessageType('Condition', (_message.Message,), dict(
    DESCRIPTOR = _OFFER_CONDITION,
    __module__ = 'offer_pb2'
    # @@protoc_insertion_point(class_scope:Offer.Condition)
    ))
  ,
  DESCRIPTOR = _OFFER,
  __module__ = 'offer_pb2'
  # @@protoc_insertion_point(class_scope:Offer)
  ))
_sym_db.RegisterMessage(Offer)
_sym_db.RegisterMessage(Offer.Asset)
_sym_db.RegisterMessage(Offer.Condition)


# @@protoc_insertion_point(module_scope)
