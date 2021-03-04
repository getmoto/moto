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


if sys.version_info[0] < 3:
    # Tests for unicode removals (Python 2 only)
    def _verify_no_unicode(blob):
        """Verify that no unicode values exist"""
        if type(blob) == dict:
            for key, value in blob.items():
                assert type(key) != unicode
                _verify_no_unicode(value)

        elif type(blob) in [list, set]:
            for item in blob:
                _verify_no_unicode(item)

        assert blob != unicode

    def test_py2_strip_unicode_keys():
        bad_dict = {
            "some": "value",
            "a": {"nested": ["List", "of", {"unicode": "values"}]},
            "and a": {"nested", "set", "of", 5, "values"},
        }

        result = py2_strip_unicode_keys(copy.deepcopy(bad_dict))
        _verify_no_unicode(result)
