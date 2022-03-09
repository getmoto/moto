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

    # Verify there are no dictionaries, network interfaces or associated
    # security groups.
    result = client.describe_directories()
    assert len(result["DirectoryDescriptions"]) == 0
    result = ec2_client.describe_network_interfaces()
    assert len(result["NetworkInterfaces"]) == 0
    result = ec2_client.describe_security_groups()
    for group in result["SecurityGroups"]:
        assert "directory controllers" not in group["Description"]

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
    assert not limits["CloudOnlyMicrosoftADCurrentCount"]
    assert not limits["ConnectedDirectoriesCurrentCount"]


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
        assert dir_info["VpcSettings"]["SecurityGroupId"].startswith("sg-")
        assert len(dir_info["DnsIpAddrs"]) == 2
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


@mock_ec2
@mock_ds
def test_ds_create_alias():
    """Test good and bad invocations of create_alias()."""
    client = boto3.client("ds", region_name=TEST_REGION)
    ec2_client = boto3.client("ec2", region_name=TEST_REGION)

    # Create a directory we can test against.
    directory_id = create_test_directory(client, ec2_client)

    # Bad format.
    bad_alias = f"d-{get_random_hex(10)}"
    with pytest.raises(ClientError) as exc:
        client.create_alias(DirectoryId=directory_id, Alias=bad_alias)
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        rf"Value '{bad_alias}' at 'alias' failed to satisfy constraint: "
        rf"Member must satisfy regular expression pattern: "
        rf"^(?!D-|d-)([\da-zA-Z]+)([-]*[\da-zA-Z])*$"
    ) in err["Message"]

    # Too long.
    bad_alias = f"d-{get_random_hex(62)}"
    with pytest.raises(ClientError) as exc:
        client.create_alias(DirectoryId=directory_id, Alias=bad_alias)
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        f"Value '{bad_alias}' at 'alias' failed to satisfy constraint: "
        f"Member must have length less than or equal to 62"
    ) in err["Message"]

    # Just right.
    good_alias = f"{get_random_hex(10)}"
    result = client.create_alias(DirectoryId=directory_id, Alias=good_alias)
    assert result["DirectoryId"] == directory_id
    assert result["Alias"] == good_alias
    result = client.describe_directories()
    directory = result["DirectoryDescriptions"][0]
    assert directory["Alias"] == good_alias
    assert directory["AccessUrl"] == f"{good_alias}.awsapps.com"

    # Attempt to create another alias for the same directory.
    another_good_alias = f"{get_random_hex(10)}"
    with pytest.raises(ClientError) as exc:
        client.create_alias(DirectoryId=directory_id, Alias=another_good_alias)
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterException"
    assert (
        "The directory in the request already has an alias. That alias must "
        "be deleted before a new alias can be created."
    ) in err["Message"]

    # Create a second directory we can test against.
    directory_id2 = create_test_directory(client, ec2_client)
    with pytest.raises(ClientError) as exc:
        client.create_alias(DirectoryId=directory_id2, Alias=good_alias)
    err = exc.value.response["Error"]
    assert err["Code"] == "EntityAlreadyExistsException"
    assert f"Alias '{good_alias}' already exists." in err["Message"]


@mock_ec2
@mock_ds
def test_ds_enable_sso():
    """Test good and bad invocations of enable_sso()."""
    client = boto3.client("ds", region_name=TEST_REGION)
    ec2_client = boto3.client("ec2", region_name=TEST_REGION)

    # Create a directory we can test against.
    directory_id = create_test_directory(client, ec2_client)

    # Need an alias before setting SSO.
    with pytest.raises(ClientError) as exc:
        client.enable_sso(DirectoryId=directory_id)
    err = exc.value.response["Error"]
    assert err["Code"] == "ClientException"
    assert (
        f"An alias is required before enabling SSO. DomainId={directory_id}"
    ) in err["Message"]

    # Add the alias to continue testing.
    client.create_alias(DirectoryId=directory_id, Alias="anything-goes")

    # Password must be less than 128 chars in length.
    good_username = "test"
    bad_password = f"bad_password{get_random_hex(128)}"
    with pytest.raises(ClientError) as exc:
        client.enable_sso(
            DirectoryId=directory_id, UserName=good_username, Password=bad_password
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        "Value at 'ssoPassword' failed to satisfy constraint: Member must "
        "have length less than or equal to 128"
    ) in err["Message"]

    # Username has constraints.
    bad_username = "@test"
    good_password = "password"
    with pytest.raises(ClientError) as exc:
        client.enable_sso(
            DirectoryId=directory_id, UserName=bad_username, Password=good_password
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        rf"Value '{bad_username}' at 'userName' failed to satisfy constraint: "
        rf"Member must satisfy regular expression pattern: ^[a-zA-Z0-9._-]+$"
    ) in err["Message"]

    # Valid execution.
    client.enable_sso(DirectoryId=directory_id)
    result = client.describe_directories()
    directory = result["DirectoryDescriptions"][0]
    assert directory["SsoEnabled"]


@mock_ec2
@mock_ds
def test_ds_disable_sso():
    """Test good and bad invocations of disable_sso()."""
    client = boto3.client("ds", region_name=TEST_REGION)
    ec2_client = boto3.client("ec2", region_name=TEST_REGION)

    # Create a directory we can test against.
    directory_id = create_test_directory(client, ec2_client)

    # Password must be less than 128 chars in length.
    good_username = "test"
    bad_password = f"bad_password{get_random_hex(128)}"
    with pytest.raises(ClientError) as exc:
        client.disable_sso(
            DirectoryId=directory_id, UserName=good_username, Password=bad_password
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        "Value at 'ssoPassword' failed to satisfy constraint: Member must "
        "have length less than or equal to 128"
    ) in err["Message"]

    # Username has constraints.
    bad_username = "@test"
    good_password = "password"
    with pytest.raises(ClientError) as exc:
        client.disable_sso(
            DirectoryId=directory_id, UserName=bad_username, Password=good_password
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        rf"Value '{bad_username}' at 'userName' failed to satisfy constraint: "
        rf"Member must satisfy regular expression pattern: ^[a-zA-Z0-9._-]+$"
    ) in err["Message"]

    # Valid execution.  First enable SSO, as the default is disabled SSO.
    client.create_alias(DirectoryId=directory_id, Alias="anything-goes")
    client.enable_sso(DirectoryId=directory_id)
    client.disable_sso(DirectoryId=directory_id)
    result = client.describe_directories()
    directory = result["DirectoryDescriptions"][0]
    assert not directory["SsoEnabled"]
