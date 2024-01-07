import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_aws
def test_create_application():
    client = boto3.client("appconfig", region_name="ap-southeast-1")
    post = client.create_application(Name="testapp", Description="blah")

    assert "Id" in post
    assert post["Name"] == "testapp"
    assert post["Description"] == "blah"

    get = client.get_application(ApplicationId=post["Id"])
    assert post["Id"] == get["Id"]
    assert post["Name"] == get["Name"]
    assert post["Description"] == get["Description"]

    update = client.update_application(
        ApplicationId=post["Id"],
        Name="name2",
        Description="desc2",
    )
    assert update["Name"] == "name2"
    assert update["Description"] == "desc2"

    client.delete_application(ApplicationId=post["Id"])

    with pytest.raises(ClientError) as exc:
        client.get_application(ApplicationId=post["Id"])
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"


@mock_aws
def test_tag_application():
    client = boto3.client("appconfig", region_name="us-east-2")
    app_id = client.create_application(Name="testapp")["Id"]
    app_arn = f"arn:aws:appconfig:us-east-2:123456789012:application/{app_id}"

    tags = client.list_tags_for_resource(ResourceArn=app_arn)["Tags"]
    assert tags == {}

    client.tag_resource(
        ResourceArn=app_arn,
        Tags={"k1": "v1"},
    )

    tags = client.list_tags_for_resource(ResourceArn=app_arn)["Tags"]
    assert tags == {"k1": "v1"}

    ####
    # Check this flow works when creating an app with tags
    app_id = client.create_application(Name="testapp", Tags={"k1": "v1"})["Id"]
    app_arn = f"arn:aws:appconfig:us-east-2:123456789012:application/{app_id}"

    tags = client.list_tags_for_resource(ResourceArn=app_arn)["Tags"]
    assert tags == {"k1": "v1"}

    client.tag_resource(
        ResourceArn=app_arn,
        Tags={"k2": "v2", "k3": "v3"},
    )

    tags = client.list_tags_for_resource(ResourceArn=app_arn)["Tags"]
    assert tags == {"k1": "v1", "k2": "v2", "k3": "v3"}

    client.untag_resource(ResourceArn=app_arn, TagKeys=["k2"])

    tags = client.list_tags_for_resource(ResourceArn=app_arn)["Tags"]
    assert tags == {"k1": "v1", "k3": "v3"}

    client.untag_resource(ResourceArn=app_arn, TagKeys=["k1", "k3"])

    tags = client.list_tags_for_resource(ResourceArn=app_arn)["Tags"]
    assert tags == {}
