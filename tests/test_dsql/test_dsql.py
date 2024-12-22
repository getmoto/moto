"""Unit tests for dsql-supported APIs."""

from datetime import datetime

import boto3
from dateutil.tz import tzutc
from freezegun import freeze_time

from moto import mock_aws, settings


@mock_aws
def test_create_cluster():
    client = boto3.client("dsql", region_name="us-east-1")
    with freeze_time("2024-12-22 12:34:00"):
        resp = client.create_cluster()

    identifier = resp["identifier"]
    assert identifier is not None
    assert resp["arn"] == f"arn:aws:dsql:us-east-1:123456789012:cluster/{identifier}"
    assert resp["deletionProtectionEnabled"] is True
    assert resp["status"] == "CREATING"
    if not settings.TEST_SERVER_MODE:
        assert resp["creationTime"] == datetime(2024, 12, 22, 12, 34, tzinfo=tzutc())
