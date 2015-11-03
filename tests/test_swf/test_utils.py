from freezegun import freeze_time
from sure import expect

from moto.swf.utils import (
    decapitalize,
    now_timestamp,
)


def test_decapitalize():
    cases = {
        "fooBar": "fooBar",
        "FooBar": "fooBar",
        "FOO BAR": "fOO BAR",
    }
    for before, after in cases.iteritems():
        decapitalize(before).should.equal(after)

@freeze_time("2015-01-01 12:00:00")
def test_now_timestamp():
    now_timestamp().should.equal(1420113600.0)
