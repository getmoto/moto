"""Directory-related unit tests focusing on tag-related functionality

Simple AD directories are used for test data, but the operations are
common to the other directory types.
"""
import boto3
from botocore.exceptions import ClientError
import pytest

from moto import mock_ds
from moto.ds.models import Directory
from moto.ec2 import mock_ec2

from .test_ds_simple_ad_directory import create_test_directory, TEST_REGION


@mock_ec2
@mock_ds
def test_ds_add_tags_to_resource():
    """Test the addition of tags to a resource."""
    client = boto3.client("ds", region_name=TEST_REGION)
    ec2_client = boto3.client("ec2", region_name=TEST_REGION)
    directory_id = create_test_directory(client, ec2_client)

    # Unknown directory ID.
    bad_id = "d-0123456789"
    with pytest.raises(ClientError) as exc:
        client.add_tags_to_resource(
            ResourceId=bad_id, Tags=[{"Key": "foo", "Value": "bar"}]
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "EntityDoesNotExistException"
    assert f"Directory {bad_id} does not exist" in err["Message"]

    # Too many tags.
    tags = [
        {"Key": f"{x}", "Value": f"{x}"}
        for x in range(Directory.MAX_TAGS_PER_DIRECTORY + 1)
    ]
    with pytest.raises(ClientError) as exc:
        client.add_tags_to_resource(ResourceId=directory_id, Tags=tags)
    err = exc.value.response["Error"]
    assert err["Code"] == "TagLimitExceededException"
    assert "Tag limit exceeded" in err["Message"]

    # Bad tags.
    with pytest.raises(ClientError) as exc:
        client.add_tags_to_resource(
            ResourceId=directory_id, Tags=[{"Key": "foo!", "Value": "bar"}],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        "1 validation error detected: Value 'foo!' at 'tags.1.member.key' "
        "failed to satisfy constraint: Member must satisfy regular "
        "expression pattern"
    ) in err["Message"]

    # Successful addition of tags.
    added_tags = [{"Key": f"{x}", "Value": f"{x}"} for x in range(10)]
    client.add_tags_to_resource(ResourceId=directory_id, Tags=added_tags)
    result = client.list_tags_for_resource(ResourceId=directory_id)
    assert len(result["Tags"]) == 10
    assert result["Tags"] == added_tags


@mock_ec2
@mock_ds
def test_ds_remove_tags_from_resource():
    """Test the removal of tags to a resource."""
    client = boto3.client("ds", region_name=TEST_REGION)
    ec2_client = boto3.client("ec2", region_name=TEST_REGION)

    # Create a directory for testing purposes.
    tag_list = [
        {"Key": "one", "Value": "1"},
        {"Key": "two", "Value": "2"},
        {"Key": "three", "Value": "3"},
    ]
    directory_id = create_test_directory(client, ec2_client, tags=tag_list)

    # Untag all of the tags.  Verify there are no more tags.
    client.remove_tags_from_resource(
        ResourceId=directory_id, TagKeys=[x["Key"] for x in tag_list]
    )
    result = client.list_tags_for_resource(ResourceId=directory_id)
    assert not result["Tags"]
    assert "NextToken" not in result


@mock_ec2
@mock_ds
def test_ds_list_tags_for_resource():
    """Test ability to list all tags for a resource."""
    client = boto3.client("ds", region_name=TEST_REGION)
    ec2_client = boto3.client("ec2", region_name=TEST_REGION)

    # Create a directory to work with.
    tags = [
        {"Key": f"{x}_k", "Value": f"{x}_v"}
        for x in range(1, Directory.MAX_TAGS_PER_DIRECTORY + 1)
    ]
    directory_id = create_test_directory(client, ec2_client, tags=tags)

    # Verify limit and next token works.
    result = client.list_tags_for_resource(ResourceId=directory_id, Limit=1)
    assert len(result["Tags"]) == 1
    assert result["Tags"] == [{"Key": "1_k", "Value": "1_v"}]
    assert result["NextToken"]

    result = client.list_tags_for_resource(
        ResourceId=directory_id, Limit=10, NextToken=result["NextToken"]
    )
    assert len(result["Tags"]) == 10
    assert result["Tags"] == [
        {"Key": f"{x}_k", "Value": f"{x}_v"} for x in range(2, 12)
    ]
    assert result["NextToken"]

    # Bad directory ID.
    bad_id = "d-0123456789"
    with pytest.raises(ClientError) as exc:
        client.list_tags_for_resource(ResourceId=bad_id)
    err = exc.value.response["Error"]
    assert err["Code"] == "EntityDoesNotExistException"
    assert f"Directory {bad_id} does not exist" in err["Message"]

    # Bad next token.
    with pytest.raises(ClientError) as exc:
        client.list_tags_for_resource(ResourceId=directory_id, NextToken="foo")
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidNextTokenException"
    assert "Invalid value passed for the NextToken parameter" in err["Message"]
