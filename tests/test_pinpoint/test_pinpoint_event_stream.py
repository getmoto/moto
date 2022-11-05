"""Unit tests for pinpoint-supported APIs."""
import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import

from botocore.exceptions import ClientError
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

    resp.should.have.key("EventStream")
    resp["EventStream"].should.have.key("ApplicationId").equals(app_id)
    resp["EventStream"].should.have.key("DestinationStreamArn").equals("kinesis:arn")
    resp["EventStream"].should.have.key("LastModifiedDate")
    resp["EventStream"].should.have.key("RoleArn").equals("iam:arn")


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

    resp.should.have.key("EventStream")
    resp["EventStream"].should.have.key("ApplicationId").equals(app_id)
    resp["EventStream"].should.have.key("DestinationStreamArn").equals("kinesis:arn")
    resp["EventStream"].should.have.key("LastModifiedDate")
    resp["EventStream"].should.have.key("RoleArn").equals("iam:arn")


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

    resp.should.have.key("EventStream")
    resp["EventStream"].should.have.key("ApplicationId").equals(app_id)
    resp["EventStream"].should.have.key("DestinationStreamArn").equals("kinesis:arn")
    resp["EventStream"].should.have.key("LastModifiedDate")
    resp["EventStream"].should.have.key("RoleArn").equals("iam:arn")

    with pytest.raises(ClientError) as exc:
        client.get_event_stream(ApplicationId=app_id)
    err = exc.value.response["Error"]
    err["Code"].should.equal("NotFoundException")
    err["Message"].should.equal("Resource not found")
