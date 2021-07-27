from __future__ import unicode_literals

import copy
import sys

import pytest
import sure  # noqa
from freezegun import freeze_time

from moto.core.utils import (
    camelcase_to_underscores,
    underscores_to_camelcase,
    unix_time,
    py2_strip_unicode_keys,
    camelcase_to_pascal,
    pascal_to_camelcase,
)


@pytest.mark.parametrize(
    "input,expected",
    [
        ("theNewAttribute", "the_new_attribute"),
        ("attri bute With Space", "attribute_with_space"),
        ("FirstLetterCapital", "first_letter_capital"),
        ("ListMFADevices", "list_mfa_devices"),
    ],
)
def test_camelcase_to_underscores(input, expected):
    camelcase_to_underscores(input).should.equal(expected)


@pytest.mark.parametrize(
    "input,expected",
    [("the_new_attribute", "theNewAttribute"), ("attribute", "attribute"),],
)
def test_underscores_to_camelcase(input, expected):
    underscores_to_camelcase(input).should.equal(expected)


@pytest.mark.parametrize(
    "input,expected",
    [("TheNewAttribute", "theNewAttribute"), ("Attribute", "attribute"),],
)
def test_pascal_to_camelcase(input, expected):
    pascal_to_camelcase(input).should.equal(expected)


@pytest.mark.parametrize(
    "input,expected",
    [("theNewAttribute", "TheNewAttribute"), ("attribute", "Attribute"),],
)
def test_camelcase_to_pascal(input, expected):
    camelcase_to_pascal(input).should.equal(expected)


@freeze_time("2015-01-01 12:00:00")
def test_unix_time():
    unix_time().should.equal(1420113600.0)
