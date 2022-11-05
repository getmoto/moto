"""Unit tests for pinpoint-supported APIs."""
import boto3
import sure  # noqa # pylint: disable=unused-import

from moto import mock_pinpoint


@mock_pinpoint
def test_list_tags_for_resource_empty():
    client = boto3.client("pinpoint", region_name="ap-southeast-1")
    resp = client.create_app(CreateApplicationRequest={"Name": "myfirstapp"})
    app_arn = resp["ApplicationResponse"]["Arn"]

    resp = client.list_tags_for_resource(ResourceArn=app_arn)
    resp.should.have.key("TagsModel").equals({"tags": {}})


@mock_pinpoint
def test_list_tags_for_resource():
    client = boto3.client("pinpoint", region_name="ap-southeast-1")
    resp = client.create_app(
        CreateApplicationRequest={
            "Name": "myfirstapp",
            "tags": {"key1": "value1", "key2": "value2"},
        }
    )
    app_arn = resp["ApplicationResponse"]["Arn"]

    resp = client.list_tags_for_resource(ResourceArn=app_arn)
    resp.should.have.key("TagsModel")
    resp["TagsModel"].should.have.key("tags").equals(
        {"key1": "value1", "key2": "value2"}
    )


@mock_pinpoint
def test_tag_resource():
    client = boto3.client("pinpoint", region_name="us-east-1")
    resp = client.create_app(CreateApplicationRequest={"Name": "myfirstapp"})
    app_arn = resp["ApplicationResponse"]["Arn"]

    client.tag_resource(
        ResourceArn=app_arn, TagsModel={"tags": {"key1": "value1", "key2": "value2"}}
    )

    resp = client.list_tags_for_resource(ResourceArn=app_arn)
    resp.should.have.key("TagsModel")
    resp["TagsModel"].should.have.key("tags").equals(
        {"key1": "value1", "key2": "value2"}
    )


@mock_pinpoint
def test_untag_resource():
    client = boto3.client("pinpoint", region_name="eu-west-1")
    resp = client.create_app(
        CreateApplicationRequest={"Name": "myfirstapp", "tags": {"key1": "value1"}}
    )
    app_arn = resp["ApplicationResponse"]["Arn"]

    client.tag_resource(
        ResourceArn=app_arn, TagsModel={"tags": {"key2": "value2", "key3": "value3"}}
    )

    client.untag_resource(ResourceArn=app_arn, TagKeys=["key2"])

    resp = client.list_tags_for_resource(ResourceArn=app_arn)
    resp.should.have.key("TagsModel")
    resp["TagsModel"].should.have.key("tags").equals(
        {"key1": "value1", "key3": "value3"}
    )
