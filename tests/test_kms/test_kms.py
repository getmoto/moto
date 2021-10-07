import boto3
import sure  # noqa
from moto import mock_kms

PLAINTEXT_VECTORS = [
    b"some encodeable plaintext",
    b"some unencodeable plaintext \xec\x8a\xcf\xb6r\xe9\xb5\xeb\xff\xa23\x16",
    "some unicode characters ø˚∆øˆˆ∆ßçøˆˆçßøˆ¨¥",
]


def _get_encoded_value(plaintext):
    if isinstance(plaintext, bytes):
        return plaintext

    return plaintext.encode("utf-8")


sort = lambda l: sorted(l, key=lambda d: d.keys())


def _check_tags(key_id, created_tags, client):
    result = client.list_resource_tags(KeyId=key_id)
    actual = result.get("Tags", [])
    assert sort(created_tags) == sort(actual)

    client.untag_resource(KeyId=key_id, TagKeys=["key1"])

    actual = client.list_resource_tags(KeyId=key_id).get("Tags", [])
    expected = [{"TagKey": "key2", "TagValue": "value2"}]
    assert sort(expected) == sort(actual)


@mock_kms
def test_key_tag_on_create_key_happy():
    client = boto3.client("kms", region_name="us-east-1")

    tags = [
        {"TagKey": "key1", "TagValue": "value1"},
        {"TagKey": "key2", "TagValue": "value2"},
    ]
    key = client.create_key(Description="test-key-tagging", Tags=tags)
    _check_tags(key["KeyMetadata"]["KeyId"], tags, client)


@mock_kms
def test_key_tag_on_create_key_on_arn_happy():
    client = boto3.client("kms", region_name="us-east-1")

    tags = [
        {"TagKey": "key1", "TagValue": "value1"},
        {"TagKey": "key2", "TagValue": "value2"},
    ]
    key = client.create_key(Description="test-key-tagging", Tags=tags)
    _check_tags(key["KeyMetadata"]["Arn"], tags, client)


@mock_kms
def test_key_tag_added_happy():
    client = boto3.client("kms", region_name="us-east-1")

    key = client.create_key(Description="test-key-tagging")
    key_id = key["KeyMetadata"]["KeyId"]
    tags = [
        {"TagKey": "key1", "TagValue": "value1"},
        {"TagKey": "key2", "TagValue": "value2"},
    ]
    client.tag_resource(KeyId=key_id, Tags=tags)
    _check_tags(key_id, tags, client)


@mock_kms
def test_key_tag_added_arn_based_happy():
    client = boto3.client("kms", region_name="us-east-1")

    key = client.create_key(Description="test-key-tagging")
    key_id = key["KeyMetadata"]["Arn"]
    tags = [
        {"TagKey": "key1", "TagValue": "value1"},
        {"TagKey": "key2", "TagValue": "value2"},
    ]
    client.tag_resource(KeyId=key_id, Tags=tags)
    _check_tags(key_id, tags, client)
