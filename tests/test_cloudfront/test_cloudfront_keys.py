from uuid import uuid4

import boto3
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from moto import mock_aws
from tests import aws_verified

from .cloudfront_test_scaffolding import minimal_dist_custom_config

private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
public_key = private_key.public_key()
pem = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
)


@aws_verified
def test_create_public_key():
    client = boto3.client("cloudfront", region_name="us-east-1")

    key_id = etag = None
    try:
        public_key_config = {
            "CallerReference": (str(uuid4())),
            "Name": (str(uuid4())),
            "EncodedKey": pem.decode("utf-8"),
        }
        resp = client.create_public_key(PublicKeyConfig=public_key_config)
        # uppercase+digits{14}
        key_id = resp["PublicKey"]["Id"]
        etag = resp["ETag"]
        public_key_config["Comment"] = ""

        assert resp["ResponseMetadata"]["HTTPStatusCode"] == 201

        assert (
            resp["Location"]
            == f"https://cloudfront.amazonaws.com/2020-05-31/public-key/{key_id}"
        )
        assert resp["PublicKey"]["CreatedTime"]
        assert resp["PublicKey"]["PublicKeyConfig"] == public_key_config

        get_key = client.get_public_key(Id=key_id)

        assert get_key["ETag"] == etag
        assert get_key["PublicKey"]["Id"] == key_id
        assert get_key["PublicKey"]["PublicKeyConfig"] == public_key_config
    finally:
        if key_id:
            client.delete_public_key(Id=key_id, IfMatch=etag)


@mock_aws
def test_list_public_keys():
    client = boto3.client("cloudfront", region_name="us-east-1")

    key_list = client.list_public_keys()["PublicKeyList"]
    assert key_list == {"MaxItems": 100, "Quantity": 0}

    key = client.create_public_key(
        PublicKeyConfig={
            "CallerReference": "someref",
            "Name": "somekey",
            "EncodedKey": "some data",
        }
    )["PublicKey"]
    key_created = key["CreatedTime"]
    key_id = key["Id"]

    key_list = client.list_public_keys()["PublicKeyList"]
    assert key_list["Quantity"] == 1
    assert key_list["Items"] == [
        {
            "Id": key_id,
            "Name": "somekey",
            "CreatedTime": key_created,
            "EncodedKey": "some data\n",
            "Comment": "",
        }
    ]


@mock_aws
def test_create_public_key_group():
    client = boto3.client("cloudfront", region_name="us-east-1")

    key_id1 = client.create_public_key(
        PublicKeyConfig={
            "CallerReference": str(uuid4()),
            "Name": str(uuid4()),
            "EncodedKey": pem.decode("utf-8"),
        }
    )["PublicKey"]["Id"]

    resp = client.create_key_group(
        KeyGroupConfig={"Name": "mygroup", "Items": [key_id1]}
    )
    key_group_id = resp["KeyGroup"]["Id"]  # uuid
    assert (
        resp["Location"]
        == f"https://cloudfront.amazonaws.com/2020-05-31/key-group/{key_group_id}"
    )
    assert resp["KeyGroup"]["KeyGroupConfig"] == {"Name": "mygroup", "Items": [key_id1]}

    get_group = client.get_key_group(Id=key_group_id)
    assert get_group["ETag"] == resp["ETag"]
    assert get_group["KeyGroup"]["Id"] == key_group_id
    assert get_group["KeyGroup"]["KeyGroupConfig"]["Name"] == "mygroup"
    assert get_group["KeyGroup"]["KeyGroupConfig"]["Items"] == [key_id1]

    groups = client.list_key_groups()["KeyGroupList"]
    assert groups["Quantity"] == 1
    assert groups["Items"][0]["KeyGroup"]["Id"] == key_group_id
    assert groups["Items"][0]["KeyGroup"]["KeyGroupConfig"]["Name"] == "mygroup"

    # We can't delete the key at this point
    # Either deregister the key, or delete the group
    # Deleting the group automatically deregisters the key (but does not delete it)


@mock_aws
def test_create_distribution_with_key_groups():
    client = boto3.client("cloudfront", region_name="us-east-1")

    key_id1 = client.create_public_key(
        PublicKeyConfig={
            "CallerReference": str(uuid4()),
            "Name": str(uuid4()),
            "EncodedKey": pem.decode("utf-8"),
        }
    )["PublicKey"]["Id"]

    resp = client.create_key_group(
        KeyGroupConfig={"Name": "mygroup", "Items": [key_id1]}
    )
    key_group_id = resp["KeyGroup"]["Id"]  # uuid

    config = minimal_dist_custom_config("sth")
    config["DefaultCacheBehavior"]["TrustedKeyGroups"] = {
        "Enabled": True,
        "Quantity": 1,
        "Items": [key_group_id],
    }
    dist = client.create_distribution(DistributionConfig=config)["Distribution"]
    config = dist["DistributionConfig"]
    key_groups = config["DefaultCacheBehavior"]["TrustedKeyGroups"]
    assert key_groups == {"Enabled": True, "Quantity": 1, "Items": [key_group_id]}


@mock_aws
def test_list_public_keys_paginate():
    seen_tokens = set()
    client = boto3.client("cloudfront", region_name="us-east-1")
    expected_ids = set()
    for index in range(101):
        expected_ids.add(
            client.create_public_key(
                PublicKeyConfig={
                    "CallerReference": f"ref-{index}",
                    "Name": f"key-{index}",
                    "EncodedKey": "some data",
                }
            )["PublicKey"]["Id"]
        )
    response = client.list_public_keys()["PublicKeyList"]
    pages = [response["Items"]]
    assert len(pages[0]) == 100
    while response.get("NextMarker"):
        next_marker = response["NextMarker"]
        assert next_marker not in seen_tokens
        seen_tokens.add(next_marker)
        response = client.list_public_keys(Marker=next_marker)["PublicKeyList"]
        pages.append(response["Items"])
    ids = [key["Id"] for page in pages for key in page]
    assert [len(page) for page in pages] == [100, 1]
    assert len(ids) == 101
    assert set(ids) == expected_ids


@mock_aws
def test_list_key_groups_paginate():
    seen_tokens = set()
    client = boto3.client("cloudfront", region_name="us-east-1")
    expected_ids = {
        client.create_key_group(KeyGroupConfig={"Name": f"group-{index}", "Items": []})[
            "KeyGroup"
        ]["Id"]
        for index in range(101)
    }
    response = client.list_key_groups()["KeyGroupList"]
    pages = [response["Items"]]
    assert len(pages[0]) == 100
    while response.get("NextMarker"):
        next_marker = response["NextMarker"]
        assert next_marker not in seen_tokens
        seen_tokens.add(next_marker)
        response = client.list_key_groups(Marker=next_marker)["KeyGroupList"]
        pages.append(response["Items"])
    ids = [item["KeyGroup"]["Id"] for page in pages for item in page]
    assert [len(page) for page in pages] == [100, 1]
    assert len(ids) == 101
    assert set(ids) == expected_ids
