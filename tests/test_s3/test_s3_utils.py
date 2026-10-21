import json
from unittest.mock import patch

import pytest

from moto.s3.utils import (
    _VersionedKeyStore,
    bucket_name_from_url,
    bucket_policy_is_public,
    compute_checksum,
    cors_matches_origin,
    parse_region_from_url,
)


def test_base_url():
    assert bucket_name_from_url("https://s3.amazonaws.com/") is None


def test_localhost_bucket():
    assert bucket_name_from_url("https://wfoobar.localhost:5000/abc") == "wfoobar"


def test_localhost_without_bucket():
    assert bucket_name_from_url("https://www.localhost:5000/def") is None


def test_force_ignore_subdomain_for_bucketnames():
    with patch("moto.s3.utils.S3_IGNORE_SUBDOMAIN_BUCKETNAME", True):
        assert (
            bucket_name_from_url("https://subdomain.localhost:5000/abc/resource")
            is None
        )


def test_versioned_key_store():
    key_store = _VersionedKeyStore()

    assert not key_store

    key_store["key"] = [1]
    assert len(key_store) == 1

    key_store["key"] = 2
    assert len(key_store) == 1

    assert key_store["key"] == 2
    assert key_store.get("key") == 2
    assert key_store.get("badkey") is None
    assert key_store.get("badkey", "HELLO") == "HELLO"

    # Tests key[
    assert "badkey" not in key_store
    with pytest.raises(KeyError):
        _ = key_store["badkey"]

    assert len(key_store.getlist("key")) == 2
    assert key_store.getlist("key") == [[1], 2]
    assert key_store.getlist("badkey") is None

    key_store.setlist("key", 1)
    assert key_store.getlist("key") == [1]

    key_store.setlist("key", (1, 2))
    assert key_store.getlist("key") != (1, 2)
    assert key_store.getlist("key") == [1, 2]

    key_store.setlist("key", [[1], [2]])
    assert len(key_store["key"]) == 1
    assert key_store.getlist("key") == [[1], [2]]


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
        assert parse_region_from_url(url) == expected

    expected = "us-east-1"
    for url in [
        "http://s3.amazonaws.com/bucket",
        "http://bucket.s3.amazonaws.com",
        "https://s3.amazonaws.com/bucket",
        "https://bucket.s3.amazonaws.com",
    ]:
        assert parse_region_from_url(url) == expected


def test_parse_region_from_url_dualstack():
    expected = "us-east-1"
    for url in [
        "https://s3.dualstack.us-east-1.amazonaws.com/bucket",
        "https://bucket.s3.dualstack.us-east-1.amazonaws.com",
    ]:
        assert parse_region_from_url(url) == expected

    expected = "ap-southeast-2"
    for url in [
        "https://s3.dualstack.ap-southeast-2.amazonaws.com/bucket",
        "https://bucket.s3.dualstack.ap-southeast-2.amazonaws.com",
    ]:
        assert parse_region_from_url(url) == expected


def test_parse_region_from_url_fips():
    for url in [
        "https://s3-fips.us-east-1.amazonaws.com/bucket",
        "https://bucket.s3-fips.us-east-1.amazonaws.com",
        "https://s3.fips.us-east-1.amazonaws.com/bucket",
        "https://bucket.s3.fips.us-east-1.amazonaws.com",
    ]:
        assert parse_region_from_url(url) == "us-east-1"


def test_checksum_sha256():
    checksum = b"h9FJy0JMA4dlbyEdJYn7Wx4WIpkhMJ6YWIQZzMqKc2I="
    assert compute_checksum(b"somedata", "SHA256") == checksum
    # Unknown algorithms fallback to SHA256 for now
    assert compute_checksum(b"somedata", algorithm="unknown") == checksum


def test_checksum_sha1():
    assert compute_checksum(b"somedata", "SHA1") == b"76oxGuRIpzdMEiBhv+2VLZQOnjc="


def test_checksum_crc32():
    assert compute_checksum(b"somedata", "CRC32") == b"Uwy90A=="


def test_checksum_crc32c():
    try:
        assert compute_checksum(b"somedata", "CRC32C") == b"dB9qBQ=="
    except:  # noqa: E722 Do not use bare except
        # Optional library Can't be found - just revert to CRC32
        assert compute_checksum(b"somedata", "CRC32C") == b"Uwy90A=="


def test_checksum_crc64nvme():
    try:
        assert compute_checksum(b"somedata", "CRC64NVME") == b"1n4hOQfCfC0="
    except:  # noqa: E722 Do not use bare except
        # Optional library Can't be found - just revert to CRC32
        assert compute_checksum(b"somedata", "CRC64NVME") == b"Uwy90A=="


def test_cors_utils():
    "Fancy string matching"
    assert cors_matches_origin("a", ["a"])
    assert cors_matches_origin("b", ["a", "b"])
    assert not cors_matches_origin("c", [])
    assert not cors_matches_origin("c", ["a", "b"])

    assert cors_matches_origin("http://www.google.com", ["http://*.google.com"])
    assert cors_matches_origin("http://www.google.com", ["http://www.*.com"])
    assert cors_matches_origin("http://www.google.com", ["http://*"])
    assert cors_matches_origin("http://www.google.com", ["*"])

    assert not cors_matches_origin("http://www.google.com", ["http://www.*.org"])
    assert not cors_matches_origin("http://www.google.com", ["https://*"])


def _policy(*statements):
    return json.dumps({"Version": "2012-10-17", "Statement": list(statements)})


def _statement(**kwargs):
    statement = {
        "Effect": "Allow",
        "Action": "s3:GetObject",
        "Resource": "arn:aws:s3:::mybucket/*",
    }
    statement.update(kwargs)
    return statement


@pytest.mark.parametrize(
    "policy,expected",
    [
        pytest.param(_policy(_statement(Principal="*")), True, id="wildcard"),
        pytest.param(
            _policy(_statement(Principal={"AWS": "*"})), True, id="aws-wildcard"
        ),
        pytest.param(
            _policy(
                _statement(Principal={"AWS": ["arn:aws:iam::123456789012:root", "*"]})
            ),
            True,
            id="aws-wildcard-in-list",
        ),
        pytest.param(
            json.dumps({"Statement": _statement(Principal="*")}),
            True,
            id="single-statement-dict",
        ),
        pytest.param(
            _policy(
                _statement(Principal={"AWS": "arn:aws:iam::123456789012:root"}),
                _statement(Principal="*"),
            ),
            True,
            id="any-public-statement",
        ),
        pytest.param(
            _policy(_statement(Principal="*")).encode("utf-8"), True, id="bytes"
        ),
        pytest.param(
            _policy(_statement(Principal="*", Effect="Deny")), False, id="deny"
        ),
        pytest.param(
            _policy(
                _statement(
                    Principal="*",
                    Condition={"StringEquals": {"aws:SourceVpc": "vpc-12345678"}},
                )
            ),
            False,
            id="wildcard-with-condition",
        ),
        pytest.param(
            _policy(_statement(Principal={"AWS": "arn:aws:iam::123456789012:root"})),
            False,
            id="specific-principal",
        ),
        pytest.param(
            _policy(
                _statement(
                    Principal={
                        "AWS": [
                            "arn:aws:iam::123456789012:root",
                            "arn:aws:iam::210987654321:root",
                        ]
                    }
                )
            ),
            False,
            id="specific-principal-list",
        ),
        pytest.param(
            _policy(_statement(Principal={"Service": "s3.amazonaws.com"})),
            False,
            id="service-principal",
        ),
        pytest.param(_policy(_statement()), False, id="no-principal"),
        pytest.param(_policy(), False, id="empty-statement-list"),
        pytest.param(json.dumps({"Version": "2012-10-17"}), False, id="no-statement"),
        pytest.param("not json", False, id="invalid-json"),
        pytest.param("", False, id="empty-string"),
    ],
)
def test_bucket_policy_is_public(policy, expected):
    assert bucket_policy_is_public(policy) is expected
