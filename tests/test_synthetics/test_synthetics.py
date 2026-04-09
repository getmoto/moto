"""Unit tests for synthetics-supported APIs."""

import boto3

from moto import mock_aws


@mock_aws
def test_create_canary_and_get_canary():
    """
    Test creating a canary and retrieving it using the synthetics client.
    """
    client = boto3.client("synthetics", region_name="us-east-1")

    resp = client.create_canary(
        Name="MyCanary",
        Code={"Handler": "index.handler"},
        ArtifactS3Location="s3://moto-canary-bucket/",
        ExecutionRoleArn="arn:aws:iam::123456789012:role/service-role/myRole",
        Schedule={"Expression": "rate(5 minutes)"},
        RunConfig={"TimeoutInSeconds": 60},
        SuccessRetentionPeriodInDays=31,
        FailureRetentionPeriodInDays=31,
        RuntimeVersion="syn-nodejs-puppeteer-3.8",
        Tags={"env": "test"},
    )

    assert "Canary" in resp
    canary = resp["Canary"]
    assert canary["Name"] == "MyCanary"
    assert canary["ExecutionRoleArn"].endswith("myRole")
    assert canary["Status"]["State"] == "READY"

    # Now get the canary
    got = client.get_canary(Name="MyCanary")
    assert got["Canary"]["Name"] == "MyCanary"
    assert got["Canary"]["Tags"]["env"] == "test"


@mock_aws
def test_describe_canaries_returns_all():
    """
    Test that describe_canaries returns all created canaries.
    """
    client = boto3.client("synthetics", region_name="ap-southeast-1")

    client.create_canary(
        Name="C1",
        Code={"Handler": "index.handler"},
        ArtifactS3Location="s3://c1-bucket/",
        ExecutionRoleArn="arn:aws:iam::123456789012:role/c1",
        Schedule={"Expression": "rate(1 hour)"},
        RunConfig={"TimeoutInSeconds": 60},
        SuccessRetentionPeriodInDays=1,
        FailureRetentionPeriodInDays=1,
        RuntimeVersion="syn-nodejs-puppeteer-3.8",
    )
    client.create_canary(
        Name="C2",
        Code={"Handler": "index.handler"},
        ArtifactS3Location="s3://c2-bucket/",
        ExecutionRoleArn="arn:aws:iam::123456789012:role/c2",
        Schedule={"Expression": "rate(10 minutes)"},
        RunConfig={"TimeoutInSeconds": 30},
        SuccessRetentionPeriodInDays=2,
        FailureRetentionPeriodInDays=2,
        RuntimeVersion="syn-nodejs-puppeteer-3.8",
    )

    resp = client.describe_canaries()
    names = [c["Name"] for c in resp["Canaries"]]
    assert set(names) == {"C1", "C2"}


@mock_aws
def test_list_tags_for_resource():
    """
    Test listing tags for a canary resource using the synthetics client.
    """
    client = boto3.client("synthetics", region_name="eu-west-1")

    client.create_canary(
        Name="TaggedCanary",
        Code={"Handler": "index.handler"},
        ArtifactS3Location="s3://tags-bucket/",
        ExecutionRoleArn="arn:aws:iam::123456789012:role/tags",
        Schedule={"Expression": "rate(5 minutes)"},
        RunConfig={"TimeoutInSeconds": 60},
        SuccessRetentionPeriodInDays=1,
        FailureRetentionPeriodInDays=1,
        RuntimeVersion="syn-nodejs-puppeteer-3.8",
        Tags={"team": "qa", "priority": "high"},
    )

    # Note: we use the canary name as resourceArn in our simplified backend
    resp = client.list_tags_for_resource(ResourceArn="TaggedCanary")
    assert resp["Tags"] == {"team": "qa", "priority": "high"}
