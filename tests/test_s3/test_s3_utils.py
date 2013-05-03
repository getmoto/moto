from sure import expect
from moto.s3.utils import bucket_name_from_url


def test_base_url():
    expect(bucket_name_from_url('https://s3.amazonaws.com/')).should.equal(None)


def test_localhost_bucket():
    expect(bucket_name_from_url('https://foobar.localhost:5000/abc')).should.equal("foobar")


def test_localhost_without_bucket():
    expect(bucket_name_from_url('https://www.localhost:5000/def')).should.equal(None)
