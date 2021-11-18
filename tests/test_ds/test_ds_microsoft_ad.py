"""Directory-related unit tests for Microsoft AD Directory Services.

The logic to check the details of VPCs and Subnets is shared between the
"create directory" APIs, so it will not be repeated here.
"""
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError
import pytest

from moto import mock_ds
from moto.core.utils import get_random_hex
from moto.ec2 import mock_ec2

from .test_ds_simple_ad_directory import TEST_REGION, create_vpc, create_subnets


def create_test_microsoft_ad(ds_client, ec2_client, vpc_settings=None, tags=None):
    """Return ID of a newly created valid directory."""
    if not vpc_settings:
        good_vpc_id = create_vpc(ec2_client)
        good_subnet_ids = create_subnets(ec2_client, good_vpc_id)
        vpc_settings = {"VpcId": good_vpc_id, "SubnetIds": good_subnet_ids}

    if not tags:
        tags = []

    result = ds_client.create_microsoft_ad(
        Name=f"test-{get_random_hex(6)}.test",
        Password="4MicrosoftADPassword",
        VpcSettings=vpc_settings,
        Tags=tags,
        Edition="Standard",
    )
    return result["DirectoryId"]


@mock_ds
def test_ds_create_microsoft_ad_validations():
    """Test validation errs that aren't caught by botocore.

    Most of this validation is shared with the Simple AD directory, but
    this verifies that it is invoked from create_microsoft_ad().
    """
    client = boto3.client("ds", region_name=TEST_REGION)
    random_num = get_random_hex(6)

    # Verify ValidationException error messages are accumulated properly.
    bad_name = f"bad_name_{random_num}"
    bad_password = "bad_password"
    bad_edition = "foo"
    ok_vpc_settings = {
        "VpcId": f"vpc-{random_num}",
        "SubnetIds": [f"subnet-{random_num}01", f"subnet-{random_num}02"],
    }
    with pytest.raises(ClientError) as exc:
        client.create_microsoft_ad(
            Name=bad_name,
            Password=bad_password,
            Edition=bad_edition,
            VpcSettings=ok_vpc_settings,
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert "3 validation errors detected" in err["Message"]
    assert (
        r"Value at 'password' failed to satisfy constraint: "
        r"Member must satisfy regular expression pattern: "
        r"^(?=^.{8,64}$)((?=.*\d)(?=.*[A-Z])(?=.*[a-z])|"
        r"(?=.*\d)(?=.*[^A-Za-z0-9\s])(?=.*[a-z])|"
        r"(?=.*[^A-Za-z0-9\s])(?=.*[A-Z])(?=.*[a-z])|"
        r"(?=.*\d)(?=.*[A-Z])(?=.*[^A-Za-z0-9\s]))^.*$" in err["Message"]
    )
    assert (
        f"Value '{bad_edition}' at 'edition' failed to satisfy constraint: "
        f"Member must satisfy enum value set: [Enterprise, Standard]" in err["Message"]
    )
    assert (
        fr"Value '{bad_name}' at 'name' failed to satisfy constraint: "
        fr"Member must satisfy regular expression pattern: "
        fr"^([a-zA-Z0-9]+[\.-])+([a-zA-Z0-9])+$" in err["Message"]
    )

    too_long = (
        "Test of directory service 0123456789 0123456789 0123456789 "
        "0123456789 0123456789 0123456789 0123456789 0123456789 0123456789 "
        "0123456789 0123456789"
    )
    short_name = "a:b.c"
    with pytest.raises(ClientError) as exc:
        client.create_microsoft_ad(
            Name=f"test{random_num}.test",
            Password="TESTfoobar1",
            VpcSettings=ok_vpc_settings,
            Description=too_long,
            ShortName=short_name,
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert "2 validation errors detected" in err["Message"]
    assert (
        f"Value '{too_long}' at 'description' failed to satisfy constraint: "
        f"Member must have length less than or equal to 128" in err["Message"]
    )
    pattern = r'^[^\/:*?"<>|.]+[^\/:*?"<>|]*$'
    assert (
        f"Value '{short_name}' at 'shortName' failed to satisfy constraint: "
        f"Member must satisfy regular expression pattern: " + pattern
    ) in err["Message"]

    bad_vpc_settings = {"VpcId": f"vpc-{random_num}", "SubnetIds": ["foo"]}
    with pytest.raises(ClientError) as exc:
        client.create_microsoft_ad(
            Name=f"test{random_num}.test",
            Password="TESTfoobar1",
            VpcSettings=bad_vpc_settings,
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert "1 validation error detected" in err["Message"]
    assert (
        fr"Value '['{bad_vpc_settings['SubnetIds'][0]}']' at "
        fr"'vpcSettings.subnetIds' failed to satisfy constraint: "
        fr"Member must satisfy regular expression pattern: "
        fr"^(subnet-[0-9a-f]{{8}}|subnet-[0-9a-f]{{17}})$" in err["Message"]
    )


@mock_ec2
@mock_ds
def test_ds_create_microsoft_ad_good_args():
    """Test creation of Microsoft AD directory using good arguments."""
    client = boto3.client("ds", region_name=TEST_REGION)
    ec2_client = boto3.client("ec2", region_name=TEST_REGION)

    # Verify a good call to create_microsoft_ad()
    directory_id = create_test_microsoft_ad(client, ec2_client)
    assert directory_id.startswith("d-")

    # Verify that too many directories can't be created.
    limits = client.get_directory_limits()["DirectoryLimits"]
    for _ in range(limits["CloudOnlyMicrosoftADLimit"]):
        create_test_microsoft_ad(client, ec2_client)
    with pytest.raises(ClientError) as exc:
        create_test_microsoft_ad(client, ec2_client)
    err = exc.value.response["Error"]
    assert err["Code"] == "DirectoryLimitExceededException"
    assert (
        f"Directory limit exceeded. A maximum of "
        f"{limits['CloudOnlyMicrosoftADLimit']} "
        f"directories may be created" in err["Message"]
    )


@mock_ec2
@mock_ds
def test_ds_create_microsoft_ad_delete():
    """Test deletion of Microsoft AD directory."""
    client = boto3.client("ds", region_name=TEST_REGION)
    ec2_client = boto3.client("ec2", region_name=TEST_REGION)

    # Delete an existing directory.
    directory_id = create_test_microsoft_ad(client, ec2_client)
    result = client.delete_directory(DirectoryId=directory_id)
    assert result["DirectoryId"] == directory_id


@mock_ec2
@mock_ds
def test_ds_create_microsoft_ad_describe():
    """Test describe_directory() for Microsoft AD directory."""
    client = boto3.client("ds", region_name=TEST_REGION)
    ec2_client = boto3.client("ec2", region_name=TEST_REGION)

    # Test that if no directory IDs are specified, all are returned.
    directory_id = create_test_microsoft_ad(client, ec2_client)
    result = client.describe_directories()
    directory = result["DirectoryDescriptions"][0]

    assert len(result["DirectoryDescriptions"]) == 1
    assert directory["DesiredNumberOfDomainControllers"] == 0
    assert not directory["SsoEnabled"]
    assert directory["DirectoryId"] == directory_id
    assert directory["Name"].startswith("test-")
    assert directory["Alias"] == directory_id
    assert directory["AccessUrl"] == f"{directory_id}.awsapps.com"
    assert directory["Stage"] == "Active"
    assert directory["LaunchTime"] <= datetime.now(timezone.utc)
    assert directory["StageLastUpdatedDateTime"] <= datetime.now(timezone.utc)
    assert directory["Type"] == "MicrosoftAD"
    assert directory["VpcSettings"]["VpcId"].startswith("vpc-")
    assert len(directory["VpcSettings"]["SubnetIds"]) == 2
    assert directory["Edition"] == "Standard"
    assert len(directory["DnsIpAddrs"]) == 2
    assert "NextToken" not in result


@mock_ec2
@mock_ds
def test_ds_create_microsoft_ad_tags():
    """Test that AD directory tags can be added and retrieved."""
    client = boto3.client("ds", region_name=TEST_REGION)
    ec2_client = boto3.client("ec2", region_name=TEST_REGION)

    added_tags = [{"Key": f"{x}", "Value": f"{x}"} for x in range(10)]
    directory_id = create_test_microsoft_ad(client, ec2_client, tags=added_tags)

    result = client.list_tags_for_resource(ResourceId=directory_id)
    assert len(result["Tags"]) == 10
    assert result["Tags"] == added_tags


@mock_ec2
@mock_ds
def test_ds_get_microsoft_ad_directory_limits():
    """Test return value for directory limits."""
    client = boto3.client("ds", region_name=TEST_REGION)
    ec2_client = boto3.client("ec2", region_name=TEST_REGION)

    # Create a bunch of directories and verify the current count has been
    # updated.
    limits = client.get_directory_limits()["DirectoryLimits"]
    for _ in range(limits["CloudOnlyMicrosoftADLimit"]):
        create_test_microsoft_ad(client, ec2_client)

    limits = client.get_directory_limits()["DirectoryLimits"]
    assert (
        limits["CloudOnlyMicrosoftADLimit"]
        == limits["CloudOnlyMicrosoftADCurrentCount"]
    )
    assert limits["CloudOnlyMicrosoftADLimitReached"]
    assert not limits["ConnectedDirectoriesLimitReached"]
    assert not limits["CloudOnlyDirectoriesCurrentCount"]
