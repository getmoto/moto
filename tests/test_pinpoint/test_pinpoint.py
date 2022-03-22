"""Unit tests for pinpoint-supported APIs."""
import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import

from botocore.exceptions import ClientError
from moto import mock_pinpoint

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_pinpoint
def test_create_app():
    client = boto3.client("pinpoint", region_name="us-east-1")
    resp = client.create_app(CreateApplicationRequest={"Name": "myfirstapp"})

    resp.should.have.key("ApplicationResponse")
    resp["ApplicationResponse"].should.have.key("Arn")
    resp["ApplicationResponse"].should.have.key("Id")
    resp["ApplicationResponse"].should.have.key("Name").equals("myfirstapp")
    resp["ApplicationResponse"].should.have.key("CreationDate")


@mock_pinpoint
def test_delete_app():
    client = boto3.client("pinpoint", region_name="ap-southeast-1")
    creation = client.create_app(CreateApplicationRequest={"Name": "myfirstapp"})[
        "ApplicationResponse"
    ]
    app_id = creation["Id"]

    deletion = client.delete_app(ApplicationId=app_id)["ApplicationResponse"]
    deletion.should.equal(creation)

    with pytest.raises(ClientError) as exc:
        client.get_app(ApplicationId=app_id)
    err = exc.value.response["Error"]
    err["Code"].should.equal("NotFoundException")
    err["Message"].should.equal("Application not found")


@mock_pinpoint
def test_get_app():
    client = boto3.client("pinpoint", region_name="eu-west-1")
    resp = client.create_app(CreateApplicationRequest={"Name": "myfirstapp"})
    app_id = resp["ApplicationResponse"]["Id"]

    resp = client.get_app(ApplicationId=app_id)

    resp.should.have.key("ApplicationResponse")
    resp["ApplicationResponse"].should.have.key("Arn")
    resp["ApplicationResponse"].should.have.key("Id")
    resp["ApplicationResponse"].should.have.key("Name").equals("myfirstapp")
    resp["ApplicationResponse"].should.have.key("CreationDate")


@mock_pinpoint
def test_get_apps_initial():
    client = boto3.client("pinpoint", region_name="us-east-1")
    resp = client.get_apps()

    resp.should.have.key("ApplicationsResponse")
    resp["ApplicationsResponse"].should.equal({"Item": []})


@mock_pinpoint
def test_get_apps():
    client = boto3.client("pinpoint", region_name="us-east-1")
    resp = client.create_app(CreateApplicationRequest={"Name": "myfirstapp"})
    app_id = resp["ApplicationResponse"]["Id"]

    resp = client.get_apps()

    resp.should.have.key("ApplicationsResponse").should.have.key("Item").length_of(1)
    resp["ApplicationsResponse"]["Item"][0].should.have.key("Arn")
    resp["ApplicationsResponse"]["Item"][0].should.have.key("Id").equals(app_id)
    resp["ApplicationsResponse"]["Item"][0].should.have.key("Name").equals("myfirstapp")
    resp["ApplicationsResponse"]["Item"][0].should.have.key("CreationDate")


@mock_pinpoint
def test_update_application_settings():
    client = boto3.client("pinpoint", region_name="eu-west-1")
    resp = client.create_app(CreateApplicationRequest={"Name": "myfirstapp"})
    app_id = resp["ApplicationResponse"]["Id"]

    resp = client.update_application_settings(
        ApplicationId=app_id,
        WriteApplicationSettingsRequest={
            "CampaignHook": {"LambdaFunctionName": "lfn"},
            "CloudWatchMetricsEnabled": True,
            "EventTaggingEnabled": True,
            "Limits": {"Daily": 42},
        },
    )

    resp.should.have.key("ApplicationSettingsResource")
    app_settings = resp["ApplicationSettingsResource"]
    app_settings.should.have.key("ApplicationId").equals(app_id)
    app_settings.should.have.key("CampaignHook").equals({"LambdaFunctionName": "lfn"})
    app_settings.should.have.key("Limits").equals({"Daily": 42})
    app_settings.should.have.key("LastModifiedDate")


@mock_pinpoint
def test_get_application_settings():
    client = boto3.client("pinpoint", region_name="ap-southeast-1")
    resp = client.create_app(CreateApplicationRequest={"Name": "myfirstapp"})
    app_id = resp["ApplicationResponse"]["Id"]

    client.update_application_settings(
        ApplicationId=app_id,
        WriteApplicationSettingsRequest={
            "CampaignHook": {"LambdaFunctionName": "lfn"},
            "CloudWatchMetricsEnabled": True,
            "EventTaggingEnabled": True,
            "Limits": {"Daily": 42},
        },
    )

    resp = client.get_application_settings(ApplicationId=app_id)

    resp.should.have.key("ApplicationSettingsResource")
    app_settings = resp["ApplicationSettingsResource"]
    app_settings.should.have.key("ApplicationId").equals(app_id)
    app_settings.should.have.key("CampaignHook").equals({"LambdaFunctionName": "lfn"})
    app_settings.should.have.key("Limits").equals({"Daily": 42})
    app_settings.should.have.key("LastModifiedDate")
