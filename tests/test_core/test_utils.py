from __future__ import unicode_literals

import copy
import sys

import sure  # noqa
from freezegun import freeze_time

from moto.core.utils import (
    camelcase_to_underscores,
    underscores_to_camelcase,
    unix_time,
    py2_strip_unicode_keys,
)


def test_camelcase_to_underscores():
    cases = {
        "theNewAttribute": "the_new_attribute",
        "attri bute With Space": "attribute_with_space",
        "FirstLetterCapital": "first_letter_capital",
        "ListMFADevices": "list_mfa_devices",
    }
    for arg, expected in cases.items():
        camelcase_to_underscores(arg).should.equal(expected)


def test_underscores_to_camelcase():
    cases = {"the_new_attribute": "theNewAttribute"}
    for arg, expected in cases.items():
        underscores_to_camelcase(arg).should.equal(expected)


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
