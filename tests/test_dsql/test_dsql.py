"""Unit tests for dsql-supported APIs."""

from datetime import datetime

import boto3
from botocore.exceptions import ClientError
from dateutil.tz import tzutc
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
    if not settings.TEST_SERVER_MODE:
        assert resp["creationTime"] == datetime(2024, 12, 22, 12, 34, tzinfo=tzutc())


@mock_aws
def test_get_invalid_cluster():
    client = boto3.client("dsql", region_name=TEST_REGION)

    try:
        client.get_cluster(identifier="invalid")
    except ClientError as err:
        assert err.response["Error"]["Code"] == "ValidationException"
        assert err.response["Error"]["Message"] == "invalid Cluster Id"


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
    assert get_resp["status"] == "CREATING"
    if not settings.TEST_SERVER_MODE:
        assert get_resp["creationTime"] == datetime(
            2024, 12, 22, 12, 34, tzinfo=tzutc()
        )


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
