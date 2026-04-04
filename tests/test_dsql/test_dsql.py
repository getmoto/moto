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
    resp = client.delete_cluster(identifier=identifier)
    assert resp["identifier"] == identifier
    assert resp["status"] == "DELETING"


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
