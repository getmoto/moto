"""Directory-related unit tests common to different directory types.

Simple AD directories are used for test data, but the operations are
common to the other directory types.
"""
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError
import pytest

from moto import mock_ds
from moto.core.utils import get_random_hex
from moto.ec2 import mock_ec2

from .test_ds_simple_ad_directory import create_test_directory, TEST_REGION


@mock_ec2
@mock_ds
def test_ds_delete_directory():
    """Test good and bad invocations of delete_directory()."""
    client = boto3.client("ds", region_name=TEST_REGION)

    # Delete a directory when there are none.
    random_directory_id = f"d-{get_random_hex(10)}"
    with pytest.raises(ClientError) as exc:
        client.delete_directory(DirectoryId=random_directory_id)
    err = exc.value.response["Error"]
    assert err["Code"] == "EntityDoesNotExistException"
    assert f"Directory {random_directory_id} does not exist" in err["Message"]

    # Delete an existing directory.
    ec2_client = boto3.client("ec2", region_name=TEST_REGION)
    directory_id = create_test_directory(client, ec2_client)
    result = client.delete_directory(DirectoryId=directory_id)
    assert result["DirectoryId"] == directory_id

    # Attempt to delete a non-existent directory.
    nonexistent_id = f"d-{get_random_hex(10)}"
    with pytest.raises(ClientError) as exc:
        client.delete_directory(DirectoryId=nonexistent_id)
    err = exc.value.response["Error"]
    assert err["Code"] == "EntityDoesNotExistException"
    assert f"Directory {nonexistent_id} does not exist" in err["Message"]

    # Attempt to use an invalid directory ID.
    bad_id = get_random_hex(3)
    with pytest.raises(ClientError) as exc:
        client.delete_directory(DirectoryId=bad_id)
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert "1 validation error detected" in err["Message"]
    assert (
        f"Value '{bad_id}' at 'directoryId' failed to satisfy constraint: "
        f"Member must satisfy regular expression pattern: ^d-[0-9a-f]{{10}}$"
    ) in err["Message"]


@mock_ec2
@mock_ds
def test_ds_get_directory_limits():
    """Test return value for directory limits."""
    client = boto3.client("ds", region_name=TEST_REGION)
    ec2_client = boto3.client("ec2", region_name=TEST_REGION)

    limits = client.get_directory_limits()["DirectoryLimits"]
    assert limits["CloudOnlyDirectoriesCurrentCount"] == 0
    assert limits["CloudOnlyDirectoriesLimit"] > 0
    assert not limits["CloudOnlyDirectoriesLimitReached"]

    # Create a bunch of directories and verify the current count has been
    # updated.
    for _ in range(limits["CloudOnlyDirectoriesLimit"]):
        create_test_directory(client, ec2_client)
    limits = client.get_directory_limits()["DirectoryLimits"]
    assert (
        limits["CloudOnlyDirectoriesLimit"]
        == limits["CloudOnlyDirectoriesCurrentCount"]
    )
    assert limits["CloudOnlyDirectoriesLimitReached"]


@mock_ec2
@mock_ds
def test_ds_describe_directories():
    """Test good and bad invocations of describe_directories()."""
    client = boto3.client("ds", region_name=TEST_REGION)
    ec2_client = boto3.client("ec2", region_name=TEST_REGION)

    expected_ids = set()
    limit = 10
    for _ in range(limit):
        expected_ids.add(create_test_directory(client, ec2_client))

    # Test that if no directory IDs are specified, all are returned.
    result = client.describe_directories()
    directories = result["DirectoryDescriptions"]
    directory_ids = [x["DirectoryId"] for x in directories]

    assert len(directories) == limit
    assert set(directory_ids) == expected_ids
    for idx, dir_info in enumerate(directories):
        assert dir_info["DesiredNumberOfDomainControllers"] == 0
        assert not dir_info["SsoEnabled"]
        assert dir_info["DirectoryId"] == directory_ids[idx]
        assert dir_info["Name"].startswith("test-")
        assert dir_info["Size"] == "Large"
        assert dir_info["Alias"] == directory_ids[idx]
        assert dir_info["AccessUrl"] == f"{directory_ids[idx]}.awsapps.com"
        assert dir_info["Stage"] == "Active"
        assert dir_info["LaunchTime"] <= datetime.now(timezone.utc)
        assert dir_info["StageLastUpdatedDateTime"] <= datetime.now(timezone.utc)
        assert dir_info["Type"] == "SimpleAD"
        assert dir_info["VpcSettings"]["VpcId"].startswith("vpc-")
        assert len(dir_info["VpcSettings"]["SubnetIds"]) == 2
    assert "NextToken" not in result

    # Test with a specific directory ID.
    result = client.describe_directories(DirectoryIds=[directory_ids[5]])
    assert len(result["DirectoryDescriptions"]) == 1
    assert result["DirectoryDescriptions"][0]["DirectoryId"] == directory_ids[5]

    # Test with a bad directory ID.
    bad_id = get_random_hex(3)
    with pytest.raises(ClientError) as exc:
        client.describe_directories(DirectoryIds=[bad_id])
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        f"Value '{bad_id}' at 'directoryId' failed to satisfy constraint: "
        f"Member must satisfy regular expression pattern: ^d-[0-9a-f]{{10}}$"
    ) in err["Message"]

    # Test with an invalid next token.
    with pytest.raises(ClientError) as exc:
        client.describe_directories(NextToken="bogus")
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidNextTokenException"
    assert "Invalid value passed for the NextToken parameter" in err["Message"]

    # Test with a limit.
    result = client.describe_directories(Limit=5)
    assert len(result["DirectoryDescriptions"]) == 5
    directories = result["DirectoryDescriptions"]
    for idx in range(5):
        assert directories[idx]["DirectoryId"] == directory_ids[idx]
    assert result["NextToken"]

    result = client.describe_directories(Limit=1, NextToken=result["NextToken"])
    assert len(result["DirectoryDescriptions"]) == 1
    assert result["DirectoryDescriptions"][0]["DirectoryId"] == directory_ids[5]
