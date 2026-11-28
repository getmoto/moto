import boto3
import pytest

from moto import mock_aws


@pytest.fixture
def client():
    with mock_aws():
        yield boto3.client("kms", region_name="us-east-1")


def _paginate(client, operation, result_key, page_size, **kwargs):
    pages = list(
        client.get_paginator(operation).paginate(
            PaginationConfig={"PageSize": page_size}, **kwargs
        )
    )
    for page in pages[:-1]:
        assert len(page[result_key]) == page_size
        assert page["Truncated"] is True
        assert "NextMarker" in page
    assert pages[-1]["Truncated"] is False
    assert "NextMarker" not in pages[-1]
    return pages, [item for page in pages for item in page[result_key]]


def test_list_keys_pagination(client):
    key_ids = [client.create_key()["KeyMetadata"]["KeyId"] for _ in range(5)]

    pages, keys = _paginate(client, "list_keys", "Keys", page_size=2)

    assert len(pages) == 3
    assert [k["KeyId"] for k in keys] == key_ids


def test_list_keys_default_page_size(client):
    for _ in range(101):
        client.create_key()

    resp = client.list_keys()
    assert len(resp["Keys"]) == 100
    assert resp["Truncated"] is True

    resp = client.list_keys(Marker=resp["NextMarker"])
    assert len(resp["Keys"]) == 1
    assert resp["Truncated"] is False


def test_list_aliases_pagination(client):
    key_id = client.create_key()["KeyMetadata"]["KeyId"]
    alias_names = [f"alias/test-{i}" for i in range(5)]
    for name in alias_names:
        client.create_alias(AliasName=name, TargetKeyId=key_id)

    _, aliases = _paginate(client, "list_aliases", "Aliases", page_size=2, KeyId=key_id)

    assert [a["AliasName"] for a in aliases] == alias_names


def test_list_grants_pagination(client):
    key_id = client.create_key()["KeyMetadata"]["KeyId"]
    grant_ids = [
        client.create_grant(
            KeyId=key_id,
            GranteePrincipal="arn:aws:iam::123456789012:role/grantee",
            RetiringPrincipal="arn:aws:iam::123456789012:role/retiree",
            Operations=["Decrypt"],
        )["GrantId"]
        for _ in range(5)
    ]

    _, grants = _paginate(client, "list_grants", "Grants", page_size=2, KeyId=key_id)
    assert [g["GrantId"] for g in grants] == grant_ids

    _, grants = _paginate(
        client,
        "list_retirable_grants",
        "Grants",
        page_size=2,
        RetiringPrincipal="arn:aws:iam::123456789012:role/retiree",
    )
    assert [g["GrantId"] for g in grants] == grant_ids


def test_list_resource_tags_pagination(client):
    tags = [{"TagKey": f"key-{i}", "TagValue": f"value-{i}"} for i in range(5)]
    key_id = client.create_key(Tags=tags)["KeyMetadata"]["KeyId"]

    _, listed = _paginate(
        client, "list_resource_tags", "Tags", page_size=2, KeyId=key_id
    )

    assert listed == tags


def test_list_keys_invalid_marker(client):
    client.create_key()

    with pytest.raises(client.exceptions.InvalidMarkerException):
        client.list_keys(Marker="not-a-marker")


def test_list_grants_marker_from_different_request(client):
    key_ids = [client.create_key()["KeyMetadata"]["KeyId"] for _ in range(2)]
    for key_id in key_ids:
        for _ in range(2):
            client.create_grant(
                KeyId=key_id,
                GranteePrincipal="arn:aws:iam::123456789012:role/grantee",
                Operations=["Decrypt"],
            )
    marker = client.list_grants(KeyId=key_ids[0], Limit=1)["NextMarker"]

    with pytest.raises(client.exceptions.InvalidMarkerException):
        client.list_grants(KeyId=key_ids[1], Marker=marker)
