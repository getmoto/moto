import pytest
from sure import expect
from moto.s3.utils import (
    bucket_name_from_url,
    _VersionedKeyStore,
    parse_region_from_url,
    clean_key_name,
    undo_clean_key_name,
    compute_checksum,
)
from unittest.mock import patch


def test_base_url():
    expect(bucket_name_from_url("https://s3.amazonaws.com/")).should.equal(None)


def test_localhost_bucket():
    expect(bucket_name_from_url("https://wfoobar.localhost:5000/abc")).should.equal(
        "wfoobar"
    )


def test_localhost_without_bucket():
    expect(bucket_name_from_url("https://www.localhost:5000/def")).should.equal(None)


def test_force_ignore_subdomain_for_bucketnames():
    with patch("moto.s3.utils.S3_IGNORE_SUBDOMAIN_BUCKETNAME", True):
        expect(
            bucket_name_from_url("https://subdomain.localhost:5000/abc/resource")
        ).should.equal(None)


def test_versioned_key_store():
    d = _VersionedKeyStore()

    d.should.have.length_of(0)

    d["key"] = [1]

    d.should.have.length_of(1)

    d["key"] = 2
    d.should.have.length_of(1)

    d.should.have.key("key").being.equal(2)

    d.get.when.called_with("key").should.return_value(2)
    d.get.when.called_with("badkey").should.return_value(None)
    d.get.when.called_with("badkey", "HELLO").should.return_value("HELLO")

    # Tests key[
    d.shouldnt.have.key("badkey")
    d.__getitem__.when.called_with("badkey").should.throw(KeyError)

    d.getlist("key").should.have.length_of(2)
    d.getlist("key").should.be.equal([[1], 2])
    d.getlist("badkey").should.be.none

    d.setlist("key", 1)
    d.getlist("key").should.be.equal([1])

    d.setlist("key", (1, 2))
    d.getlist("key").shouldnt.be.equal((1, 2))
    d.getlist("key").should.be.equal([1, 2])

    d.setlist("key", [[1], [2]])
    d["key"].should.have.length_of(1)
    d.getlist("key").should.be.equal([[1], [2]])


def test_parse_region_from_url():
    expected = "us-west-2"
    for url in [
        "http://s3-us-west-2.amazonaws.com/bucket",
        "http://s3.us-west-2.amazonaws.com/bucket",
        "http://bucket.s3-us-west-2.amazonaws.com",
        "https://s3-us-west-2.amazonaws.com/bucket",
        "https://s3.us-west-2.amazonaws.com/bucket",
        "https://bucket.s3-us-west-2.amazonaws.com",
    ]:
        parse_region_from_url(url).should.equal(expected)

    expected = "us-east-1"
    for url in [
        "http://s3.amazonaws.com/bucket",
        "http://bucket.s3.amazonaws.com",
        "https://s3.amazonaws.com/bucket",
        "https://bucket.s3.amazonaws.com",
    ]:
        parse_region_from_url(url).should.equal(expected)


@pytest.mark.parametrize(
    "key,expected",
    [
        ("foo/bar/baz", "foo/bar/baz"),
        ("foo", "foo"),
        (
            "foo/run_dt%3D2019-01-01%252012%253A30%253A00",
            "foo/run_dt=2019-01-01%2012%3A30%3A00",
        ),
    ],
)
def test_clean_key_name(key, expected):
    clean_key_name(key).should.equal(expected)


@pytest.mark.parametrize(
    "key,expected",
    [
        ("foo/bar/baz", "foo/bar/baz"),
        ("foo", "foo"),
        (
            "foo/run_dt%3D2019-01-01%252012%253A30%253A00",
            "foo/run_dt%253D2019-01-01%25252012%25253A30%25253A00",
        ),
    ],
)
def test_undo_clean_key_name(key, expected):
    undo_clean_key_name(key).should.equal(expected)


def test_checksum_sha256():
    checksum = b"ODdkMTQ5Y2I0MjRjMDM4NzY1NmYyMTFkMjU4OWZiNWIxZTE2MjI5OTIxMzA5ZTk4NTg4NDE5Y2NjYThhNzM2Mg=="
    compute_checksum(b"somedata", "SHA256").should.equal(checksum)
    # Unknown algorithms fallback to SHA256 for now
    compute_checksum(b"somedata", algorithm="unknown").should.equal(checksum)


def test_checksum_sha1():
    compute_checksum(b"somedata", "SHA1").should.equal(
        b"ZWZhYTMxMWFlNDQ4YTczNzRjMTIyMDYxYmZlZDk1MmQ5NDBlOWUzNw=="
    )


def test_checksum_crc32():
    compute_checksum(b"somedata", "CRC32").should.equal(b"MTM5MzM0Mzk1Mg==")


def test_checksum_crc32c():
    compute_checksum(b"somedata", "CRC32C").should.equal(b"MTM5MzM0Mzk1Mg==")
