"""Unit tests for pinpoint-supported APIs."""
import boto3
from botocore.exceptions import ClientError
import pytest

from moto import mock_pinpoint

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_pinpoint
def test_create_app():
    client = boto3.client("pinpoint", region_name="us-east-1")
    resp = client.create_app(CreateApplicationRequest={"Name": "myfirstapp"})

    assert "ApplicationResponse" in resp
    assert "Arn" in resp["ApplicationResponse"]
    assert "Id" in resp["ApplicationResponse"]
    assert resp["ApplicationResponse"]["Name"] == "myfirstapp"
    assert "CreationDate" in resp["ApplicationResponse"]


@mock_pinpoint
def test_delete_app():
    client = boto3.client("pinpoint", region_name="ap-southeast-1")
    creation = client.create_app(CreateApplicationRequest={"Name": "myfirstapp"})[
        "ApplicationResponse"
    ]
    app_id = creation["Id"]

    deletion = client.delete_app(ApplicationId=app_id)["ApplicationResponse"]
    assert deletion == creation

    with pytest.raises(ClientError) as exc:
        client.get_app(ApplicationId=app_id)
    err = exc.value.response["Error"]
    assert err["Code"] == "NotFoundException"
    assert err["Message"] == "Application not found"


@mock_pinpoint
def test_get_app():
    client = boto3.client("pinpoint", region_name="eu-west-1")
    resp = client.create_app(CreateApplicationRequest={"Name": "myfirstapp"})
    app_id = resp["ApplicationResponse"]["Id"]

    resp = client.get_app(ApplicationId=app_id)

    assert "ApplicationResponse" in resp
    assert "Arn" in resp["ApplicationResponse"]
    assert "Id" in resp["ApplicationResponse"]
    assert resp["ApplicationResponse"]["Name"] == "myfirstapp"
    assert "CreationDate" in resp["ApplicationResponse"]


@mock_pinpoint
def test_get_apps_initial():
    client = boto3.client("pinpoint", region_name="us-east-1")
    resp = client.get_apps()

    assert "ApplicationsResponse" in resp
    assert resp["ApplicationsResponse"] == {"Item": []}


@mock_pinpoint
def test_get_apps():
    client = boto3.client("pinpoint", region_name="us-east-1")
    resp = client.create_app(CreateApplicationRequest={"Name": "myfirstapp"})
    app_id = resp["ApplicationResponse"]["Id"]

    resp = client.get_apps()

    assert len(resp["ApplicationsResponse"]["Item"]) == 1
    assert "Arn" in resp["ApplicationsResponse"]["Item"][0]
    assert resp["ApplicationsResponse"]["Item"][0]["Id"] == app_id
    assert resp["ApplicationsResponse"]["Item"][0]["Name"] == "myfirstapp"
    assert "CreationDate" in resp["ApplicationsResponse"]["Item"][0]


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

    assert "ApplicationSettingsResource" in resp
    app_settings = resp["ApplicationSettingsResource"]
    assert app_settings["ApplicationId"] == app_id
    assert app_settings["CampaignHook"] == {"LambdaFunctionName": "lfn"}
    assert app_settings["Limits"] == {"Daily": 42}
    assert "LastModifiedDate" in app_settings


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

    assert "ApplicationSettingsResource" in resp
    app_settings = resp["ApplicationSettingsResource"]
    assert app_settings["ApplicationId"] == app_id
    assert app_settings["CampaignHook"] == {"LambdaFunctionName": "lfn"}
    assert app_settings["Limits"] == {"Daily": 42}
    assert "LastModifiedDate" in app_settings
