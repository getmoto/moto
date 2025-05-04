"""Unit tests for servicecatalogappregistry-supported APIs."""

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_aws
def test_create_application():
    client = boto3.client("servicecatalog-appregistry", region_name="us-east-1")
    resp = client.create_application(name="testapp", description="blah")

    assert "id" in resp["application"]
    assert resp["application"]["name"] == "testapp"
    assert resp["application"]["description"] == "blah"


@mock_aws
def test_list_applications():
    client = boto3.client("servicecatalog-appregistry", region_name="us-east-1")
    client.create_application(name="testapp", description="blah")
    client.create_application(name="testapp2", description="foo")
    list_resp = client.list_applications()

    assert "applications" in list_resp
    assert list_resp["applications"][1]["name"] == "testapp2"
    assert list_resp["applications"][1]["description"] == "foo"


@mock_aws
def test_associate_resource():
    client = boto3.client("servicecatalog-appregistry", region_name="us-east-1")
    create = client.create_application(name="testapp", description="blah")
    resp = client.associate_resource(
        application=create["application"]["id"],
        resource="foo",
        resourceType="RESOURCE_TAG_VALUE",
        options=["APPLY_APPLICATION_TAG"],
    )

    assert "applicationArn" in resp
    assert "resourceArn" in resp
    assert "options" in resp
    assert resp["applicationArn"] == create["application"]["arn"]


@mock_aws
def test_associate_resource_fails_resource_type():
    client = boto3.client("servicecatalog-appregistry", region_name="us-east-1")
    create = client.create_application(name="testapp", description="blah")
    with pytest.raises(ClientError) as exc:
        client.associate_resource(
            application=create["application"]["id"],
            resource="foo",
            resourceType="FOO",
            options=["APPLY_APPLICATION_TAG"],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert err["Message"] == "The request has invalid or missing parameters."


@mock_aws
def test_list_associated_resources():
    client = boto3.client("servicecatalog-appregistry", region_name="us-east-1")
    create = client.create_application(name="testapp", description="blah")
    associate = client.associate_resource(
        application=create["application"]["id"],
        resource="foo",
        resourceType="RESOURCE_TAG_VALUE",
        options=["APPLY_APPLICATION_TAG"],
    )
    resp = client.list_associated_resources(application=create["application"]["arn"])

    assert "resources" in resp
    assert "options" in resp["resources"][0]
    assert "arn" in resp["resources"][0]
    assert "resourceDetails" in resp["resources"][0]
    assert resp["resources"][0]["options"] == associate["options"]
