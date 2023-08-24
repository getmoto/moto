"""Unit tests for pinpoint-supported APIs."""
import boto3
from botocore.exceptions import ClientError
import pytest

from moto import mock_pinpoint

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_pinpoint
def test_put_event_stream():
    client = boto3.client("pinpoint", region_name="eu-west-1")
    resp = client.create_app(CreateApplicationRequest={"Name": "myfirstapp"})
    app_id = resp["ApplicationResponse"]["Id"]

    resp = client.put_event_stream(
        ApplicationId=app_id,
        WriteEventStream={"DestinationStreamArn": "kinesis:arn", "RoleArn": "iam:arn"},
    )

    assert "EventStream" in resp
    assert resp["EventStream"]["ApplicationId"] == app_id
    assert resp["EventStream"]["DestinationStreamArn"] == "kinesis:arn"
    assert "LastModifiedDate" in resp["EventStream"]
    assert resp["EventStream"]["RoleArn"] == "iam:arn"


@mock_pinpoint
def test_get_event_stream():
    client = boto3.client("pinpoint", region_name="us-east-1")
    resp = client.create_app(CreateApplicationRequest={"Name": "myfirstapp"})
    app_id = resp["ApplicationResponse"]["Id"]

    client.put_event_stream(
        ApplicationId=app_id,
        WriteEventStream={"DestinationStreamArn": "kinesis:arn", "RoleArn": "iam:arn"},
    )

    resp = client.get_event_stream(ApplicationId=app_id)

    assert "EventStream" in resp
    assert resp["EventStream"]["ApplicationId"] == app_id
    assert resp["EventStream"]["DestinationStreamArn"] == "kinesis:arn"
    assert "LastModifiedDate" in resp["EventStream"]
    assert resp["EventStream"]["RoleArn"] == "iam:arn"


@mock_pinpoint
def test_delete_event_stream():
    client = boto3.client("pinpoint", region_name="us-east-1")
    resp = client.create_app(CreateApplicationRequest={"Name": "myfirstapp"})
    app_id = resp["ApplicationResponse"]["Id"]

    client.put_event_stream(
        ApplicationId=app_id,
        WriteEventStream={"DestinationStreamArn": "kinesis:arn", "RoleArn": "iam:arn"},
    )

    resp = client.delete_event_stream(ApplicationId=app_id)

    assert "EventStream" in resp
    assert resp["EventStream"]["ApplicationId"] == app_id
    assert resp["EventStream"]["DestinationStreamArn"] == "kinesis:arn"
    assert "LastModifiedDate" in resp["EventStream"]
    assert resp["EventStream"]["RoleArn"] == "iam:arn"

    with pytest.raises(ClientError) as exc:
        client.get_event_stream(ApplicationId=app_id)
    err = exc.value.response["Error"]
    assert err["Code"] == "NotFoundException"
    assert err["Message"] == "Resource not found"
