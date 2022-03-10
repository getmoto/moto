import pytest
import sure  # noqa # pylint: disable=unused-import
from freezegun import freeze_time

from moto.core.utils import (
    camelcase_to_underscores,
    underscores_to_camelcase,
    unix_time,
    camelcase_to_pascal,
    pascal_to_camelcase,
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
def test_camelcase_to_underscores(_input, expected):
    camelcase_to_underscores(_input).should.equal(expected)


@pytest.mark.parametrize(
    "_input,expected",
    [("the_new_attribute", "theNewAttribute"), ("attribute", "attribute")],
)
def test_underscores_to_camelcase(_input, expected):
    underscores_to_camelcase(_input).should.equal(expected)


@pytest.mark.parametrize(
    "_input,expected",
    [("TheNewAttribute", "theNewAttribute"), ("Attribute", "attribute")],
)
def test_pascal_to_camelcase(_input, expected):
    pascal_to_camelcase(_input).should.equal(expected)


@pytest.mark.parametrize(
    "_input,expected",
    [("theNewAttribute", "TheNewAttribute"), ("attribute", "Attribute")],
)
def test_camelcase_to_pascal(_input, expected):
    camelcase_to_pascal(_input).should.equal(expected)


@freeze_time("2015-01-01 12:00:00")
def test_unix_time():
    unix_time().should.equal(1420113600.0)
