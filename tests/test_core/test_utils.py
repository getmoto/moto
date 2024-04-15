import datetime

import pytest
from freezegun import freeze_time

from moto.core.utils import (
    camelcase_to_pascal,
    camelcase_to_underscores,
    pascal_to_camelcase,
    rfc_1123_datetime,
    str_to_rfc_1123_datetime,
    underscores_to_camelcase,
    unix_time,
)


@pytest.mark.parametrize(
    "_input,expected",
    [
        ("theNewAttribute", "the_new_attribute"),
        ("attri bute With Space", "attribute_with_space"),
        ("FirstLetterCapital", "first_letter_capital"),
        ("ListMFADevices", "list_mfa_devices"),
    ],
)
def test_camelcase_to_underscores(_input: str, expected: str) -> None:
    assert camelcase_to_underscores(_input) == expected


@pytest.mark.parametrize(
    "_input,expected",
    [("the_new_attribute", "theNewAttribute"), ("attribute", "attribute")],
)
def test_underscores_to_camelcase(_input: str, expected: str) -> None:
    assert underscores_to_camelcase(_input) == expected


@pytest.mark.parametrize(
    "_input,expected",
    [("TheNewAttribute", "theNewAttribute"), ("Attribute", "attribute")],
)
def test_pascal_to_camelcase(_input: str, expected: str) -> None:
    assert pascal_to_camelcase(_input) == expected


@pytest.mark.parametrize(
    "_input,expected",
    [("theNewAttribute", "TheNewAttribute"), ("attribute", "Attribute")],
)
def test_camelcase_to_pascal(_input: str, expected: str) -> None:
    assert camelcase_to_pascal(_input) == expected


@freeze_time("2015-01-01 12:00:00")
def test_unix_time() -> None:  # type: ignore[misc]
    assert unix_time() == 1420113600.0


def test_rfc1123_dates() -> None:
    with freeze_time("2012-03-04 05:00:05"):
        x = rfc_1123_datetime(datetime.datetime.now())
        assert x == "Sun, 04 Mar 2012 05:00:05 GMT"
        assert str_to_rfc_1123_datetime(x) == datetime.datetime.now()
