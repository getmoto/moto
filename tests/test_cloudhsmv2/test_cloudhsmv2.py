"""Unit tests for cloudhsmv2-supported APIs."""

import boto3

from moto import mock_aws

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_aws
def test_list_tags():
    client = boto3.client("cloudhsmv2", region_name="eu-west-1")

    # Create tags for a resource
    resource_id = "cluster-1234"
    client.tag_resource(
        ResourceId=resource_id,
        TagList=[
            {"Key": "Environment", "Value": "Production"},
            {"Key": "Project", "Value": "Security"},
        ],
    )

    # Test listing all tags
    response = client.list_tags(ResourceId=resource_id)
    assert len(response["TagList"]) == 2
    assert {"Key": "Environment", "Value": "Production"} in response["TagList"]
    assert {"Key": "Project", "Value": "Security"} in response["TagList"]
    assert "NextToken" not in response

    # Test pagination
    response = client.list_tags(ResourceId=resource_id, MaxResults=1)
    assert len(response["TagList"]) == 1
    assert "NextToken" in response

    # Get next page
    response = client.list_tags(
        ResourceId=resource_id, MaxResults=1, NextToken=response["NextToken"]
    )
    assert len(response["TagList"]) == 1
    assert "NextToken" not in response


@mock_aws
def test_tag_resource():
    client = boto3.client("cloudhsmv2", region_name="eu-west-1")
    resource_id = "cluster-1234"

    # Test adding new tags
    response = client.tag_resource(
        ResourceId=resource_id,
        TagList=[
            {"Key": "Environment", "Value": "Production"},
            {"Key": "Project", "Value": "Security"},
        ],
    )

    # Verify tags were added
    tags = client.list_tags(ResourceId=resource_id)["TagList"]
    assert len(tags) == 2
    assert {"Key": "Environment", "Value": "Production"} in tags
    assert {"Key": "Project", "Value": "Security"} in tags

    # Test updating existing tag
    response = client.tag_resource(
        ResourceId=resource_id,
        TagList=[
            {"Key": "Environment", "Value": "Development"}  # Update existing tag
        ],
    )

    # Verify tag was updated
    tags = client.list_tags(ResourceId=resource_id)["TagList"]
    assert len(tags) == 2
    assert {"Key": "Environment", "Value": "Development"} in tags
    assert {"Key": "Project", "Value": "Security"} in tags


@mock_aws
def test_list_tags_empty_resource():
    client = boto3.client("cloudhsmv2", region_name="eu-west-1")

    # Test listing tags for resource with no tags
    response = client.list_tags(ResourceId="non-existent-resource")
    assert response["TagList"] == []
    assert "NextToken" not in response


@mock_aws
def test_untag_resource():
    client = boto3.client("cloudhsmv2", region_name="ap-southeast-1")
    resp = client.untag_resource()

    raise Exception("NotYetImplemented")
