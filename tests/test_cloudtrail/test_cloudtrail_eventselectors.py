import boto3
import pytest

from moto import mock_cloudtrail, mock_s3
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

from .test_cloudtrail import create_trail_simple


@mock_cloudtrail
@mock_s3
def test_put_event_selectors():
    client = boto3.client("cloudtrail", region_name="eu-west-1")
    _, _, trail_name = create_trail_simple(region_name="eu-west-1")

    resp = client.put_event_selectors(
        TrailName=trail_name,
        EventSelectors=[
            {
                "ReadWriteType": "All",
                "IncludeManagementEvents": True,
                "DataResources": [
                    {"Type": "AWS::S3::Object", "Values": ["arn:aws:s3:::*/*"]}
                ],
            }
        ],
    )

    assert "TrailARN" in resp
    assert resp["EventSelectors"] == [
        {
            "ReadWriteType": "All",
            "IncludeManagementEvents": True,
            "DataResources": [
                {"Type": "AWS::S3::Object", "Values": ["arn:aws:s3:::*/*"]}
            ],
        }
    ]
    assert "AdvancedEventSelectors" not in resp


@mock_cloudtrail
@mock_s3
def test_put_event_selectors_advanced():
    client = boto3.client("cloudtrail", region_name="eu-west-1")
    _, _, trail_name = create_trail_simple(region_name="eu-west-1")

    resp = client.put_event_selectors(
        TrailName=trail_name,
        EventSelectors=[
            {
                "ReadWriteType": "All",
                "IncludeManagementEvents": True,
                "DataResources": [
                    {"Type": "AWS::S3::Object", "Values": ["arn:aws:s3:::*/*"]}
                ],
            }
        ],
        AdvancedEventSelectors=[
            {"Name": "aes1", "FieldSelectors": [{"Field": "f", "Equals": ["fs1"]}]}
        ],
    )

    assert "TrailARN" in resp
    assert resp["EventSelectors"] == [
        {
            "ReadWriteType": "All",
            "IncludeManagementEvents": True,
            "DataResources": [
                {"Type": "AWS::S3::Object", "Values": ["arn:aws:s3:::*/*"]}
            ],
        }
    ]
    assert resp["AdvancedEventSelectors"] == [
        {"Name": "aes1", "FieldSelectors": [{"Field": "f", "Equals": ["fs1"]}]}
    ]


@mock_cloudtrail
@mock_s3
def test_get_event_selectors_empty():
    client = boto3.client("cloudtrail", region_name="ap-southeast-1")
    _, _, trail_name = create_trail_simple(region_name="ap-southeast-1")

    resp = client.get_event_selectors(TrailName=trail_name)

    assert (
        resp["TrailARN"]
        == f"arn:aws:cloudtrail:ap-southeast-1:{ACCOUNT_ID}:trail/{trail_name}"
    )
    assert resp["EventSelectors"] == []
    assert resp["AdvancedEventSelectors"] == []


@mock_cloudtrail
@mock_s3
def test_get_event_selectors():
    client = boto3.client("cloudtrail", region_name="ap-southeast-2")
    _, _, trail_name = create_trail_simple(region_name="ap-southeast-2")

    client.put_event_selectors(
        TrailName=trail_name,
        EventSelectors=[
            {
                "ReadWriteType": "All",
                "IncludeManagementEvents": False,
                "DataResources": [
                    {"Type": "AWS::S3::Object", "Values": ["arn:aws:s3:::*/*"]}
                ],
            }
        ],
    )

    resp = client.get_event_selectors(TrailName=trail_name)

    assert (
        resp["TrailARN"]
        == f"arn:aws:cloudtrail:ap-southeast-2:{ACCOUNT_ID}:trail/{trail_name}"
    )
    assert resp["EventSelectors"] == [
        {
            "ReadWriteType": "All",
            "IncludeManagementEvents": False,
            "DataResources": [
                {"Type": "AWS::S3::Object", "Values": ["arn:aws:s3:::*/*"]}
            ],
        }
    ]


@mock_cloudtrail
@mock_s3
def test_get_event_selectors_multiple():
    client = boto3.client("cloudtrail", region_name="ap-southeast-1")
    _, _, trail_name = create_trail_simple(region_name="ap-southeast-1")

    client.put_event_selectors(
        TrailName=trail_name,
        EventSelectors=[
            {
                "ReadWriteType": "All",
                "IncludeManagementEvents": False,
                "DataResources": [
                    {"Type": "AWS::S3::Object", "Values": ["arn:aws:s3:::*/*"]}
                ],
            }
        ],
    )

    client.put_event_selectors(
        TrailName=trail_name,
        AdvancedEventSelectors=[
            {"Name": "aes1", "FieldSelectors": [{"Field": "f", "Equals": ["fs1"]}]}
        ],
    )

    resp = client.get_event_selectors(TrailName=trail_name)

    assert "TrailARN" in resp
    # Setting advanced selectors cancels any existing event selectors
    assert resp["EventSelectors"] == []
    assert resp["AdvancedEventSelectors"] == [
        {"Name": "aes1", "FieldSelectors": [{"Field": "f", "Equals": ["fs1"]}]}
    ]


@mock_cloudtrail
@mock_s3
@pytest.mark.parametrize("using_arn", [True, False])
def test_put_insight_selectors(using_arn):
    client = boto3.client("cloudtrail", region_name="us-east-2")
    _, resp, trail_name = create_trail_simple(region_name="us-east-2")

    resp = client.put_insight_selectors(
        TrailName=trail_name, InsightSelectors=[{"InsightType": "ApiCallRateInsight"}]
    )

    assert "TrailARN" in resp
    assert resp["InsightSelectors"] == [{"InsightType": "ApiCallRateInsight"}]

    if using_arn:
        trail_arn = resp["TrailARN"]
        resp = client.get_insight_selectors(TrailName=trail_arn)
    else:
        resp = client.get_insight_selectors(TrailName=trail_name)

    assert "TrailARN" in resp
    assert resp["InsightSelectors"] == [{"InsightType": "ApiCallRateInsight"}]


@mock_cloudtrail
@mock_s3
def test_get_insight_selectors():
    client = boto3.client("cloudtrail", region_name="eu-west-1")
    _, resp, trail_name = create_trail_simple(region_name="eu-west-1")
    resp = client.get_insight_selectors(TrailName=trail_name)

    assert "TrailARN" in resp
    assert "InsightSelectors" not in resp
