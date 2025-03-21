"""Unit tests for servicecatalogappregistry-supported APIs."""

import boto3

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
