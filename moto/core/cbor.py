"""Encoder and decoder for the subset of CBOR (RFC 8949) used by the Smithy RPC v2 CBOR protocol.

https://smithy.io/2.0/additional-specs/protocols/smithy-rpc-v2-cbor.html

The structure mirrors botocore's CBORSerializer (botocore/serialize.py) and
BaseCBORParser (botocore/parsers.py), but Moto's implementation operates on
plain Python values instead of Botocore model shapes.

Moto's parsers and serializers already handle the Shape-specific conversions.
"""

from __future__ import annotations

import calendar
import io
import math
import os
import struct
from collections.abc import Mapping
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any


class CBORDecodeError(Exception):
    pass


class CBOREncodeError(Exception):
    pass


UNSIGNED_INT_MAJOR_TYPE = 0
NEGATIVE_INT_MAJOR_TYPE = 1
BLOB_MAJOR_TYPE = 2
STRING_MAJOR_TYPE = 3
LIST_MAJOR_TYPE = 4
MAP_MAJOR_TYPE = 5
TAG_MAJOR_TYPE = 6
FLOAT_AND_SIMPLE_MAJOR_TYPE = 7

EPOCH_DATETIME_TAG = 1
POSITIVE_BIGNUM_TAG = 2
NEGATIVE_BIGNUM_TAG = 3
DECIMAL_FRACTION_TAG = 4

INDEFINITE_ITEM_ADDITIONAL_INFO = 31
BREAK_CODE = 0xFF

MAX_UINT64 = 2**64 - 1


class CBOREncoder:
    def encode(self, value: Any) -> bytes:
        serialized = bytearray()
        self._serialize_data_item(serialized, value)
        return bytes(serialized)

    def _serialize_data_item(self, serialized: bytearray, value: Any) -> None:
        # bool must be checked before int, because bool is a subclass of int.
        if value is None:
            self._serialize_type_null(serialized)
        elif isinstance(value, bool):
            self._serialize_type_boolean(serialized, value)
        elif isinstance(value, int):
            self._serialize_type_integer(serialized, value)
        elif isinstance(value, float):
            self._serialize_type_float(serialized, value)
        elif isinstance(value, Decimal):
            self._serialize_type_decimal(serialized, value)
        elif isinstance(value, str):
            self._serialize_type_string(serialized, value)
        elif isinstance(value, (bytes, bytearray)):
            self._serialize_type_blob(serialized, value)
        elif isinstance(value, datetime):
            self._serialize_type_timestamp(serialized, value)
        elif isinstance(value, (list, tuple)):
            self._serialize_type_list(serialized, value)
        elif isinstance(value, Mapping):
            self._serialize_type_map(serialized, value)
        else:
            raise CBOREncodeError(
                f"Unable to serialize value of type {type(value).__name__} to CBOR"
            )

    def _serialize_type_integer(self, serialized: bytearray, value: int) -> None:
        if value >= 0:
            major_type = UNSIGNED_INT_MAJOR_TYPE
        else:
            major_type = NEGATIVE_INT_MAJOR_TYPE
            value = -1 - value
        if value > MAX_UINT64:
            self._serialize_type_bignum(serialized, value, major_type)
            return
        self._serialize_head(serialized, major_type, value)

    def _serialize_type_bignum(
        self, serialized: bytearray, value: int, major_type: int
    ) -> None:
        tag = (
            POSITIVE_BIGNUM_TAG
            if major_type == UNSIGNED_INT_MAJOR_TYPE
            else NEGATIVE_BIGNUM_TAG
        )
        self._serialize_head(serialized, TAG_MAJOR_TYPE, tag)
        self._serialize_type_blob(
            serialized, value.to_bytes((value.bit_length() + 7) // 8, "big")
        )

    def _serialize_type_decimal(self, serialized: bytearray, value: Decimal) -> None:
        # Tag 4 is a decimal fraction: an array of [exponent, mantissa].
        sign, digits, exponent = value.as_tuple()
        if not isinstance(exponent, int):
            raise CBOREncodeError(f"Unable to serialize Decimal value {value} to CBOR")
        mantissa = int("".join(str(d) for d in digits) or "0")
        if sign:
            mantissa = -mantissa
        self._serialize_head(serialized, TAG_MAJOR_TYPE, DECIMAL_FRACTION_TAG)
        self._serialize_type_list(serialized, [exponent, mantissa])

    def _serialize_type_blob(
        self, serialized: bytearray, value: bytes | bytearray
    ) -> None:
        self._serialize_head(serialized, BLOB_MAJOR_TYPE, len(value))
        serialized.extend(value)

    def _serialize_type_string(self, serialized: bytearray, value: str) -> None:
        encoded = value.encode("utf-8")
        self._serialize_head(serialized, STRING_MAJOR_TYPE, len(encoded))
        serialized.extend(encoded)

    def _serialize_type_list(
        self, serialized: bytearray, value: list[Any] | tuple[Any, ...]
    ) -> None:
        self._serialize_head(serialized, LIST_MAJOR_TYPE, len(value))
        for item in value:
            self._serialize_data_item(serialized, item)

    def _serialize_type_map(
        self, serialized: bytearray, value: Mapping[Any, Any]
    ) -> None:
        self._serialize_head(serialized, MAP_MAJOR_TYPE, len(value))
        for key_item, item in value.items():
            self._serialize_data_item(serialized, key_item)
            self._serialize_data_item(serialized, item)

    def _serialize_type_timestamp(self, serialized: bytearray, value: datetime) -> None:
        # Smithy spec: timestamps are epoch seconds with millisecond precision,
        # wrapped in tag 1. Naive datetimes are assumed to be UTC.
        if value.tzinfo is not None:
            value = value.astimezone(timezone.utc)
        timestamp: int | float = calendar.timegm(value.timetuple())
        if value.microsecond:
            timestamp += (value.microsecond // 1000) / 1000.0
        self._serialize_head(serialized, TAG_MAJOR_TYPE, EPOCH_DATETIME_TAG)
        self._serialize_data_item(serialized, timestamp)

    def _serialize_type_float(self, serialized: bytearray, value: float) -> None:
        if self._is_special_number(value):
            # Handle special values like NaN or Infinity
            serialized.extend(self._get_bytes_for_special_numbers(value))
        elif struct.unpack(">f", struct.pack(">f", value))[0] == value:
            # Smithy spec: use the smallest representation that does not lose precision.
            serialized.extend(
                self._get_initial_byte(FLOAT_AND_SIMPLE_MAJOR_TYPE, 26)
                + struct.pack(">f", value)
            )
        else:
            serialized.extend(
                self._get_initial_byte(FLOAT_AND_SIMPLE_MAJOR_TYPE, 27)
                + struct.pack(">d", value)
            )

    def _serialize_type_boolean(self, serialized: bytearray, value: bool) -> None:
        additional_info = 21 if value else 20
        serialized.extend(
            self._get_initial_byte(FLOAT_AND_SIMPLE_MAJOR_TYPE, additional_info)
        )

    def _serialize_type_null(self, serialized: bytearray) -> None:
        serialized.extend(self._get_initial_byte(FLOAT_AND_SIMPLE_MAJOR_TYPE, 22))

    def _serialize_head(
        self, serialized: bytearray, major_type: int, value: int
    ) -> None:
        # Writes the initial byte, followed by the argument (an integer value,
        # a length, or a tag number) if it does not fit in the initial byte.
        additional_info, num_bytes = self._get_additional_info_and_num_bytes(value)
        initial_byte = self._get_initial_byte(major_type, additional_info)
        if num_bytes == 0:
            serialized.extend(initial_byte)
        else:
            serialized.extend(initial_byte + value.to_bytes(num_bytes, "big"))

    @staticmethod
    def _get_additional_info_and_num_bytes(value: int) -> tuple[int, int]:
        # Values under 24 can be stored in the initial byte and don't need further
        # encoding
        if value < 24:
            return value, 0
        # Values between 24 and 255 (inclusive) can be stored in 1 byte and
        # correspond to additional info 24
        elif value < 256:
            return 24, 1
        # Values up to 65535 can be stored in two bytes and correspond to additional
        # info 25
        elif value < 65536:
            return 25, 2
        # Values up to 4294967296 can be stored in four bytes and correspond to
        # additional info 26
        elif value < 4294967296:
            return 26, 4
        # The maximum number of bytes in a definite length data items is 8 which
        # to additional info 27
        else:
            return 27, 8

    @staticmethod
    def _get_initial_byte(major_type: int, additional_info: int) -> bytes:
        # The highest order three bits are the major type,
        # so  we need  to bitshift the major type by 5
        major_type_bytes = major_type << 5
        return (major_type_bytes | additional_info).to_bytes(1, "big")

    @staticmethod
    def _is_special_number(value: float) -> bool:
        return math.isinf(value) or math.isnan(value)

    def _get_bytes_for_special_numbers(self, value: float) -> bytes:
        initial_byte = self._get_initial_byte(FLOAT_AND_SIMPLE_MAJOR_TYPE, 25)
        if math.isnan(value):
            return initial_byte + struct.pack(">H", 0x7E00)
        elif value > 0:
            return initial_byte + struct.pack(">H", 0x7C00)
        return initial_byte + struct.pack(">H", 0xFC00)


class CBORDecoder:
    def __init__(self) -> None:
        self.major_type_to_parsing_method_map = {
            UNSIGNED_INT_MAJOR_TYPE: self._parse_unsigned_integer,
            NEGATIVE_INT_MAJOR_TYPE: self._parse_negative_integer,
            BLOB_MAJOR_TYPE: self._parse_byte_string,
            STRING_MAJOR_TYPE: self._parse_text_string,
            LIST_MAJOR_TYPE: self._parse_array,
            MAP_MAJOR_TYPE: self._parse_map,
            TAG_MAJOR_TYPE: self._parse_tag,
            FLOAT_AND_SIMPLE_MAJOR_TYPE: self._parse_simple_and_float,
        }

    def decode(self, data: bytes) -> Any:
        stream = io.BufferedReader(io.BytesIO(data))
        value = self.parse_data_item(stream)
        if stream.peek(1)[:1]:
            raise CBORDecodeError("Unexpected data found after the CBOR data item")
        return value

    def parse_data_item(self, stream: io.BufferedReader[io.BytesIO]) -> Any:
        # CBOR data is divided into "data items", and each data item starts
        # with an initial byte that describes how the following bytes should be parsed
        initial_byte = self._read_bytes_as_int(stream, 1)
        # The highest order three bits of the initial byte describe the CBOR major type
        major_type = initial_byte >> 5
        # The lowest order 5 bits of the initial byte tells us more information about
        # how the bytes should be parsed that will be used
        additional_info = initial_byte & 0b00011111
        method = self.major_type_to_parsing_method_map[major_type]
        return method(stream, additional_info)

    # Major type 0 - unsigned integers
    def _parse_unsigned_integer(
        self, stream: io.BufferedReader[io.BytesIO], additional_info: int
    ) -> int:
        additional_info_to_num_bytes = {
            24: 1,
            25: 2,
            26: 4,
            27: 8,
        }
        # Values under 24 don't need a full byte to be stored; their values are
        # instead stored as the "additional info" in the initial byte
        if additional_info < 24:
            return additional_info
        elif additional_info in additional_info_to_num_bytes:
            num_bytes = additional_info_to_num_bytes[additional_info]
            return self._read_bytes_as_int(stream, num_bytes)
        else:
            raise CBORDecodeError(
                "Invalid CBOR integer; unparsable additional info found "
                f"for major type 0 or 1: {additional_info}"
            )

    # Major type 1 - negative integers
    def _parse_negative_integer(
        self, stream: io.BufferedReader[io.BytesIO], additional_info: int
    ) -> int:
        return -1 - self._parse_unsigned_integer(stream, additional_info)

    # Major type 2 - byte string
    def _parse_byte_string(
        self, stream: io.BufferedReader[io.BytesIO], additional_info: int
    ) -> bytes:
        if additional_info != INDEFINITE_ITEM_ADDITIONAL_INFO:
            length = self._parse_unsigned_integer(stream, additional_info)
            return self._read_from_stream(stream, length)
        else:
            chunks = []
            while True:
                if self._handle_break_code(stream):
                    break
                initial_byte = self._read_bytes_as_int(stream, 1)
                additional_info = initial_byte & 0b00011111
                length = self._parse_unsigned_integer(stream, additional_info)
                chunks.append(self._read_from_stream(stream, length))
            return b"".join(chunks)

    # Major type 3 - text string
    def _parse_text_string(
        self, stream: io.BufferedReader[io.BytesIO], additional_info: int
    ) -> str:
        return self._parse_byte_string(stream, additional_info).decode("utf-8")

    # Major type 4 - lists
    def _parse_array(
        self, stream: io.BufferedReader[io.BytesIO], additional_info: int
    ) -> list[Any]:
        if additional_info != INDEFINITE_ITEM_ADDITIONAL_INFO:
            length = self._parse_unsigned_integer(stream, additional_info)
            return [self.parse_data_item(stream) for _ in range(length)]
        else:
            items = []
            while not self._handle_break_code(stream):
                items.append(self.parse_data_item(stream))
            return items

    # Major type 5 - maps
    def _parse_map(
        self, stream: io.BufferedReader[io.BytesIO], additional_info: int
    ) -> dict[Any, Any]:
        items: dict[Any, Any] = {}
        if additional_info != INDEFINITE_ITEM_ADDITIONAL_INFO:
            length = self._parse_unsigned_integer(stream, additional_info)
            for _ in range(length):
                self._parse_key_value_pair(stream, items)
        else:
            while not self._handle_break_code(stream):
                self._parse_key_value_pair(stream, items)
        return items

    def _parse_key_value_pair(
        self, stream: io.BufferedReader[io.BytesIO], items: dict[Any, Any]
    ) -> None:
        # Unlike botocore, null values are kept so that sparse maps can be represented.
        # Moto's parsers drop them when walking structures.
        key = self.parse_data_item(stream)
        value = self.parse_data_item(stream)
        items[key] = value

    # Major type 6 - tags
    def _parse_tag(
        self, stream: io.BufferedReader[io.BytesIO], additional_info: int
    ) -> Any:
        tag = self._parse_unsigned_integer(stream, additional_info)
        value = self.parse_data_item(stream)
        if tag == EPOCH_DATETIME_TAG:
            return self._parse_datetime(value)
        elif tag == POSITIVE_BIGNUM_TAG and isinstance(value, bytes):
            return int.from_bytes(value, "big")
        elif tag == NEGATIVE_BIGNUM_TAG and isinstance(value, bytes):
            return -1 - int.from_bytes(value, "big")
        elif (
            tag == DECIMAL_FRACTION_TAG
            and isinstance(value, list)
            and len(value) == 2
            and all(isinstance(v, int) for v in value)
        ):
            exponent, mantissa = value
            return Decimal(mantissa).scaleb(exponent)
        raise CBORDecodeError(f"Found unsupported CBOR tag: {tag}")

    @staticmethod
    def _parse_datetime(value: Any) -> datetime:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return datetime.fromtimestamp(value, tz=timezone.utc)
        raise CBORDecodeError(f"Unable to parse datetime value: {value}")

    # Major type 7 includes floats and "simple" types.  Supported simple types are
    # currently boolean values, CBOR's null, and CBOR's undefined type.  All other
    # values are either floats or invalid.
    def _parse_simple_and_float(
        self, stream: io.BufferedReader[io.BytesIO], additional_info: int
    ) -> bool | float | None:
        # For major type 7, values 20-23 correspond to CBOR "simple" values
        additional_info_simple_values = {
            20: False,  # CBOR false
            21: True,  # CBOR true
            22: None,  # CBOR null
            23: None,  # CBOR undefined
        }
        # First we check if the additional info corresponds to a supported simple value
        if additional_info in additional_info_simple_values:
            return additional_info_simple_values[additional_info]

        # If it's not a simple value, we need to parse it into the correct format and
        # number of bytes
        float_formats = {
            25: (">e", 2),
            26: (">f", 4),
            27: (">d", 8),
        }

        if additional_info in float_formats:
            float_format, num_bytes = float_formats[additional_info]
            return struct.unpack(
                float_format, self._read_from_stream(stream, num_bytes)
            )[0]
        raise CBORDecodeError(
            f"Invalid additional info found for major type 7: {additional_info}.  "
            f"This indicates an unsupported simple type or an indefinite float value"
        )

    # This helper method is intended for use when parsing indefinite length items.
    # It does nothing if the next byte is not the break code.  If the next byte is
    # the break code, it advances past that byte and returns True so the calling
    # method knows to stop parsing that data item.
    @staticmethod
    def _handle_break_code(stream: io.BufferedReader[io.BytesIO]) -> bool:
        if int.from_bytes(stream.peek(1)[:1], "big") == BREAK_CODE:
            stream.seek(1, os.SEEK_CUR)
            return True
        return False

    def _read_bytes_as_int(
        self, stream: io.BufferedReader[io.BytesIO], num_bytes: int
    ) -> int:
        byte = self._read_from_stream(stream, num_bytes)
        return int.from_bytes(byte, "big")

    @staticmethod
    def _read_from_stream(
        stream: io.BufferedReader[io.BytesIO], num_bytes: int
    ) -> bytes:
        value = stream.read(num_bytes)
        if len(value) != num_bytes:
            raise CBORDecodeError(
                "End of stream reached; this indicates malformed CBOR data"
            )
        return value


def dumps(value: Any) -> bytes:
    return CBOREncoder().encode(value)


def loads(data: bytes) -> Any:
    return CBORDecoder().decode(data)
