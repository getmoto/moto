"""Unit tests for dsql-supported APIs."""

from datetime import datetime, timezone

import boto3
import pytest
from botocore.exceptions import ClientError
from freezegun import freeze_time

from moto import mock_aws, settings

TEST_REGION = "us-east-1"


@mock_aws
def test_create_cluster():
    client = boto3.client("dsql", region_name=TEST_REGION)
    with freeze_time("2024-12-22 12:34:00"):
        resp = client.create_cluster()

    identifier = resp["identifier"]
    assert identifier is not None
    assert resp["arn"] == f"arn:aws:dsql:us-east-1:123456789012:cluster/{identifier}"
    assert resp["deletionProtectionEnabled"] is True
    assert resp["status"] == "CREATING"
    assert resp["encryptionDetails"] == {
        "encryptionStatus": "ENABLED",
        "encryptionType": "AWS_OWNED_KMS_KEY",
    }
    if not settings.TEST_SERVER_MODE:
        assert resp["creationTime"] == datetime(
            2024, 12, 22, 12, 34, tzinfo=timezone.utc
        )


@mock_aws
def test_create_cluster_with_tags():
    client = boto3.client("dsql", region_name=TEST_REGION)
    tags = {"foo": "bar", "baz": "qux"}
    resp = client.create_cluster(tags=tags)
    cluster_arn = resp["arn"]
    resp = client.list_tags_for_resource(resourceArn=cluster_arn)
    assert resp["tags"] == tags


@mock_aws
def test_delete_cluster():
    client = boto3.client("dsql", region_name=TEST_REGION)
    resp = client.create_cluster()
    identifier = resp["identifier"]
    client.update_cluster(identifier=identifier, deletionProtectionEnabled=False)
    resp = client.delete_cluster(identifier=identifier)
    assert resp["identifier"] == identifier
    assert resp["status"] == "DELETING"


@mock_aws
def test_delete_cluster_with_deletion_protection():
    client = boto3.client("dsql", region_name=TEST_REGION)
    identifier = client.create_cluster()["identifier"]
    with pytest.raises(client.exceptions.ConflictException):
        client.delete_cluster(identifier=identifier)


@mock_aws
def test_delete_non_existent_cluster():
    client = boto3.client("dsql", region_name=TEST_REGION)
    with pytest.raises(ClientError) as exc:
        client.delete_cluster(identifier="non-existent-cluster")
    resp = exc.value.response
    assert resp["Error"]["Code"] == "ResourceNotFoundException"
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 404
    assert resp["resourceId"] == "non-existent-cluster"
    assert resp["resourceType"] == "cluster"


@mock_aws
def test_get_invalid_cluster():
    client = boto3.client("dsql", region_name=TEST_REGION)

    try:
        client.get_cluster(identifier="invalid")
    except ClientError as err:
        assert err.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_get_cluster():
    client = boto3.client("dsql", region_name=TEST_REGION)
    with freeze_time("2024-12-22 12:34:00"):
        resp = client.create_cluster()

    identifier = resp["identifier"]

    get_resp = client.get_cluster(identifier=identifier)

    # TODO Add `witnessRegion` and `linkedClusterArns` when implement create-multi-region-clusters
    assert get_resp["identifier"] == identifier
    assert (
        get_resp["arn"] == f"arn:aws:dsql:us-east-1:123456789012:cluster/{identifier}"
    )
    assert get_resp["deletionProtectionEnabled"] is True
    assert get_resp["status"] == "ACTIVE"
    if not settings.TEST_SERVER_MODE:
        assert get_resp["creationTime"] == datetime(
            2024, 12, 22, 12, 34, tzinfo=timezone.utc
        )


@mock_aws
def test_get_vpc_endpoint_service_name():
    client = boto3.client("dsql", region_name=TEST_REGION)
    resp = client.create_cluster()
    identifier = resp["identifier"]
    endpoint = resp["endpoint"]
    resp = client.get_vpc_endpoint_service_name(identifier=identifier)
    assert resp["clusterVpcEndpoint"] == endpoint


@mock_aws()
def test_generate_tokens():
    client = boto3.client("dsql", TEST_REGION)

    hostname = "dsql.amazonaws.com"

    admin_url = client.generate_db_connect_admin_auth_token(Hostname=hostname)
    assert admin_url.startswith(hostname)
    assert "Action=DbConnectAdmin" in admin_url

    url = client.generate_db_connect_auth_token(Hostname=hostname)
    assert url.startswith(hostname)
    assert "Action=DbConnect" in url


@mock_aws
def test_list_clusters_with_pagination():
    client = boto3.client("dsql", region_name=TEST_REGION)
    identifiers = [client.create_cluster()["identifier"] for _ in range(3)]

    pages = list(
        client.get_paginator("list_clusters").paginate(PaginationConfig={"PageSize": 1})
    )

    assert [c["identifier"] for page in pages for c in page["clusters"]] == identifiers


@mock_aws
def test_update_cluster():
    client = boto3.client("dsql", region_name=TEST_REGION)
    identifier = client.create_cluster()["identifier"]

    client.update_cluster(
        identifier=identifier,
        deletionProtectionEnabled=False,
        kmsEncryptionKey="arn:aws:kms:us-east-1:123456789012:key/example",
        multiRegionProperties={"witnessRegion": "us-west-2"},
    )

    cluster = client.get_cluster(identifier=identifier)
    assert cluster["deletionProtectionEnabled"] is False
    assert cluster["multiRegionProperties"] == {"witnessRegion": "us-west-2"}
    assert cluster["encryptionDetails"] == {
        "encryptionStatus": "ENABLED",
        "encryptionType": "CUSTOMER_MANAGED_KMS_KEY",
        "kmsKeyArn": "arn:aws:kms:us-east-1:123456789012:key/example",
    }


@mock_aws
def test_tag_and_untag_cluster():
    client = boto3.client("dsql", region_name=TEST_REGION)
    cluster = client.create_cluster(tags={"existing": "tag"})

    client.tag_resource(resourceArn=cluster["arn"], tags={"new": "tag"})
    assert client.list_tags_for_resource(resourceArn=cluster["arn"])["tags"] == {
        "existing": "tag",
        "new": "tag",
    }

    client.untag_resource(resourceArn=cluster["arn"], tagKeys=["existing"])
    assert client.list_tags_for_resource(resourceArn=cluster["arn"])["tags"] == {
        "new": "tag"
    }


@mock_aws
def test_cluster_policy_lifecycle():
    client = boto3.client("dsql", region_name=TEST_REGION)
    identifier = client.create_cluster()["identifier"]
    policy = '{"Version":"2012-10-17","Statement":[]}'

    put_response = client.put_cluster_policy(identifier=identifier, policy=policy)
    get_response = client.get_cluster_policy(identifier=identifier)
    assert get_response == {
        "policy": policy,
        "policyVersion": put_response["policyVersion"],
        "ResponseMetadata": get_response["ResponseMetadata"],
    }

    delete_response = client.delete_cluster_policy(identifier=identifier)
    assert delete_response["policyVersion"] != put_response["policyVersion"]
    with pytest.raises(client.exceptions.ResourceNotFoundException):
        client.get_cluster_policy(identifier=identifier)


@mock_aws
def test_cluster_policy_expected_version():
    client = boto3.client("dsql", region_name=TEST_REGION)
    identifier = client.create_cluster()["identifier"]
    policy = '{"Version":"2012-10-17","Statement":[]}'
    response = client.put_cluster_policy(identifier=identifier, policy=policy)

    with pytest.raises(client.exceptions.ConflictException):
        client.put_cluster_policy(
            identifier=identifier,
            policy=policy,
            expectedPolicyVersion="outdated",
        )

    client.delete_cluster_policy(
        identifier=identifier,
        expectedPolicyVersion=response["policyVersion"],
    )


@mock_aws
def test_create_cluster_is_idempotent():
    client = boto3.client("dsql", region_name=TEST_REGION)
    token = "a" * 32
    first = client.create_cluster(clientToken=token)
    second = client.create_cluster(clientToken=token)
    assert second["identifier"] == first["identifier"]


def _create_stream(client, cluster_identifier, **kwargs):
    return client.create_stream(
        clusterIdentifier=cluster_identifier,
        targetDefinition={
            "kinesis": {
                "streamArn": "arn:aws:kinesis:us-east-1:123456789012:stream/changes",
                "roleArn": "arn:aws:iam::123456789012:role/dsql-stream",
            }
        },
        ordering="UNORDERED",
        format="JSON",
        **kwargs,
    )


@mock_aws
def test_stream_lifecycle():
    client = boto3.client("dsql", region_name=TEST_REGION)
    cluster_identifier = client.create_cluster()["identifier"]

    created = _create_stream(client, cluster_identifier, tags={"environment": "test"})
    stream_identifier = created["streamIdentifier"]
    assert created["status"] == "CREATING"

    stream = client.get_stream(
        clusterIdentifier=cluster_identifier,
        streamIdentifier=stream_identifier,
    )
    assert stream["status"] == "ACTIVE"
    assert stream["format"] == "JSON"
    assert stream["ordering"] == "UNORDERED"
    assert stream["targetDefinition"]["kinesis"]["roleArn"].endswith("role/dsql-stream")
    assert stream["tags"] == {"environment": "test"}

    deleted = client.delete_stream(
        clusterIdentifier=cluster_identifier,
        streamIdentifier=stream_identifier,
    )
    assert deleted["status"] == "DELETING"
    with pytest.raises(client.exceptions.ResourceNotFoundException):
        client.get_stream(
            clusterIdentifier=cluster_identifier,
            streamIdentifier=stream_identifier,
        )


@mock_aws
def test_list_streams_with_pagination():
    client = boto3.client("dsql", region_name=TEST_REGION)
    cluster_identifier = client.create_cluster()["identifier"]
    stream_identifiers = [
        _create_stream(client, cluster_identifier)["streamIdentifier"] for _ in range(3)
    ]

    pages = list(
        client.get_paginator("list_streams").paginate(
            clusterIdentifier=cluster_identifier,
            PaginationConfig={"PageSize": 1},
        )
    )

    assert [
        s["streamIdentifier"] for page in pages for s in page["streams"]
    ] == stream_identifiers


@mock_aws
def test_tag_and_untag_stream():
    client = boto3.client("dsql", region_name=TEST_REGION)
    cluster_identifier = client.create_cluster()["identifier"]
    stream = _create_stream(client, cluster_identifier)

    client.tag_resource(resourceArn=stream["arn"], tags={"key": "value"})
    assert client.list_tags_for_resource(resourceArn=stream["arn"])["tags"] == {
        "key": "value"
    }
    client.untag_resource(resourceArn=stream["arn"], tagKeys=["key"])
    assert client.list_tags_for_resource(resourceArn=stream["arn"])["tags"] == {}


@mock_aws
def test_stream_operations_validate_resources():
    client = boto3.client("dsql", region_name=TEST_REGION)
    with pytest.raises(client.exceptions.ResourceNotFoundException):
        _create_stream(client, "0" * 26)
