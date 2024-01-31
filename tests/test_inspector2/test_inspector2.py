import boto3

from moto import mock_aws

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_aws
def test_create_filter():
    client = boto3.client("inspector2", region_name="us-east-2")
    resp = client.create_filter(
        name="my_first_filter",
        reason="because I said so",
        action="NONE",
        description="my filter",
        filterCriteria={
            "codeVulnerabilityDetectorName": [{"comparison": "EQUALS", "value": "cvdn"}]
        },
    )
    assert "arn" in resp


@mock_aws
def test_list_filters():
    client = boto3.client("inspector2", region_name="ap-southeast-1")
    assert client.list_filters()["filters"] == []

    arn1 = client.create_filter(
        name="my_first_filter",
        action="NONE",
        filterCriteria={"findingArn": [{"comparison": "EQUALS", "value": "cvdn"}]},
    )["arn"]

    filters = client.list_filters()["filters"]
    assert len(filters) == 1
    assert filters[0]["arn"] == arn1

    arn2 = client.create_filter(
        name="my_second_filter",
        action="SUPPRESS",
        filterCriteria={"fixAvailable": [{"comparison": "EQUALS", "value": "cvdn"}]},
    )["arn"]

    filters = client.list_filters()["filters"]
    assert len(filters) == 2

    filters = client.list_filters(action="SUPPRESS")["filters"]
    assert len(filters) == 1
    assert filters[0]["arn"] == arn2

    filters = client.list_filters(arns=[arn1])["filters"]
    assert len(filters) == 1
    assert filters[0]["arn"] == arn1

    client.delete_filter(arn=arn1)

    filters = client.list_filters()["filters"]
    assert len(filters) == 1
    assert filters[0]["arn"] == arn2
