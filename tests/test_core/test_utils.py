from __future__ import unicode_literals

import sure  # noqa
from freezegun import freeze_time

from moto.core.utils import camelcase_to_underscores, underscores_to_camelcase, unix_time, merge_taglists


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
    cases = {
        "the_new_attribute": "theNewAttribute",
    }
    for arg, expected in cases.items():
        underscores_to_camelcase(arg).should.equal(expected)


@freeze_time("2015-01-01 12:00:00")
def test_unix_time():
    unix_time().should.equal(1420113600.0)


def test_merge_taglists():
    taglist_a = [
        {
            'Key': 'foo',
            'Value': 'bar',
        },
        {
            'Key': 'foo1',
            'Value': 'bar1',
        },
    ]
    taglist_b = [
        {
            'Key': 'foo1',
            'Value': 'bar1b',
        },
    ]
    taglist_merged = merge_taglists(taglist_a, taglist_b)
    len(taglist_merged).should.equal(2)
    tag_foo = [t for t in taglist_merged if t['Key']=='foo']
    tag_foo1 = [t for t in taglist_merged if t['Key']=='foo1']
    tag_foo[0].should.equal({'Key': 'foo','Value': 'bar',})
    tag_foo1[0].should.equal({'Key': 'foo1','Value': 'bar1b',})
