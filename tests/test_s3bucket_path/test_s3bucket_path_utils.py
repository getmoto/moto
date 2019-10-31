from __future__ import unicode_literals
from sure import expect
from moto.s3bucket_path.utils import bucket_name_from_url


def test_base_url():
    expect(bucket_name_from_url("https://s3.amazonaws.com/")).should.equal(None)


def test_localhost_bucket():
    expect(bucket_name_from_url("https://localhost:5000/wfoobar/abc")).should.equal(
        "wfoobar"
    )


def test_localhost_without_bucket():
    expect(bucket_name_from_url("https://www.localhost:5000")).should.equal(None)
