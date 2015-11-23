from __future__ import unicode_literals
import sure

from moto.core.utils import camelcase_to_underscores


def test_camelcase_to_underscores():
    cases = {
        "theNewAttribute": "the_new_attribute",
        "attri bute With Space": "attribute_with_space",
        "FirstLetterCapital": "first_letter_capital",
    }
    for arg, expected in cases.items():
        camelcase_to_underscores(arg).should.equal(expected)
