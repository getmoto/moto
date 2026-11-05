from __future__ import annotations

import math
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from moto.core import cbor


@pytest.mark.parametrize(
    "value,encoded",
    [
        # Examples from RFC 8949, Appendix A
        (0, "00"),
        (23, "17"),
        (24, "1818"),
        (255, "18ff"),
        (256, "190100"),
        (65535, "19ffff"),
        (65536, "1a00010000"),
        (4294967295, "1affffffff"),
        (4294967296, "1b0000000100000000"),
        (18446744073709551615, "1bffffffffffffffff"),
        (18446744073709551616, "c249010000000000000000"),
        (-1, "20"),
        (-24, "37"),
        (-25, "3818"),
        (-1000, "3903e7"),
        (-18446744073709551617, "c349010000000000000000"),
        (False, "f4"),
        (True, "f5"),
        (None, "f6"),
        (1.5, "fa3fc00000"),
        (1.1, "fb3ff199999999999a"),
        (float("inf"), "f97c00"),
        (float("-inf"), "f9fc00"),
        (b"\x01\x02\x03\x04", "4401020304"),
        ("", "60"),
        ("IETF", "6449455446"),
        ("ü", "62c3bc"),
        ([], "80"),
        ([1, [2, 3], [4, 5]], "8301820203820405"),
        ({}, "a0"),
        ({"a": 1, "b": [2, 3]}, "a26161016162820203"),
        (Decimal("273.15"), "c48221196ab3"),
        (Decimal("-273.15"), "c48221396ab2"),
    ],
)
def test_encode_and_decode(value: object, encoded: str) -> None:
    assert cbor.dumps(value).hex() == encoded
    assert cbor.loads(bytes.fromhex(encoded)) == value


def test_encode_nan() -> None:
    encoded = cbor.dumps(float("nan"))
    assert encoded.hex() == "f97e00"
    assert math.isnan(cbor.loads(encoded))


@pytest.mark.parametrize(
    "encoded,expected",
    [
        # Half-precision floats must be accepted, even though we never send them
        ("f93c00", 1.0),
        ("f97bff", 65504.0),
        ("f90001", 5.960464477539063e-08),
        ("f9fc00", float("-inf")),
        # Undefined is deserialized to null
        ("f7", None),
    ],
)
def test_decode_simple_and_float(encoded: str, expected: float | None) -> None:
    assert cbor.loads(bytes.fromhex(encoded)) == expected


@pytest.mark.parametrize(
    "encoded,expected",
    [
        ("5f42010243030405ff", b"\x01\x02\x03\x04\x05"),
        ("7f657374726561646d696e67ff", "streaming"),
        ("9fff", []),
        ("9f018202039f0405ffff", [1, [2, 3], [4, 5]]),
        ("bf61610161629f0203ffff", {"a": 1, "b": [2, 3]}),
        ("bf6346756ef563416d7421ff", {"Fun": True, "Amt": -2}),
    ],
)
def test_decode_indefinite_length(encoded: str, expected: object) -> None:
    assert cbor.loads(bytes.fromhex(encoded)) == expected


def test_decode_keeps_null_values() -> None:
    # Sparse maps and lists may contain nulls
    assert cbor.loads(bytes.fromhex("a2616101616280")) == {"a": 1, "b": []}
    assert cbor.loads(bytes.fromhex("a16161f6")) == {"a": None}
    assert cbor.loads(bytes.fromhex("8201f6")) == [1, None]


def test_timestamps() -> None:
    whole_seconds = datetime(2013, 3, 21, 20, 4, 0, tzinfo=timezone.utc)
    assert cbor.dumps(whole_seconds).hex() == "c11a514b67b0"
    assert cbor.loads(bytes.fromhex("c11a514b67b0")) == whole_seconds

    # Epoch seconds as a float, truncated to millisecond precision
    fractional = datetime(2000, 1, 2, 20, 34, 56, 123456, tzinfo=timezone.utc)
    assert cbor.loads(cbor.dumps(fractional)) == fractional.replace(microsecond=123000)

    # Naive datetimes are assumed to be UTC
    assert cbor.dumps(whole_seconds.replace(tzinfo=None)) == cbor.dumps(whole_seconds)


@pytest.mark.parametrize(
    "encoded",
    [
        # Truncated data
        "19ff",
        "6449",
        "82",
        # Unsupported tag
        "d82076687474703a2f2f7777772e6578616d706c652e636f6d",
        # Timestamp that isn't a number
        "c16161",
        # Trailing data
        "0000",
        # Unsupported simple value
        "f0",
        # Integer with reserved additional info
        "1c",
    ],
)
def test_decode_invalid(encoded: str) -> None:
    with pytest.raises(cbor.CBORDecodeError):
        cbor.loads(bytes.fromhex(encoded))


@pytest.mark.parametrize(
    "value", [object(), Decimal("NaN"), Decimal("sNaN"), Decimal("Infinity")]
)
def test_encode_unsupported_value(value: object) -> None:
    with pytest.raises(cbor.CBOREncodeError):
        cbor.dumps(value)
