import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws, settings
from moto.moto_api._internal import mock_random

TEST_REGION = "us-east-1" if settings.TEST_SERVER_MODE else "us-west-2"


def create_vpc(ec2_client):
    """Return the ID for a valid VPC."""
    return ec2_client.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]["VpcId"]


def create_subnets(
    ec2_client, vpc_id, region1=TEST_REGION + "a", region2=TEST_REGION + "b"
):
    """Return list of two subnets IDs."""
    subnet_ids = []
    for cidr_block, region in [("10.0.1.0/24", region1), ("10.0.0.0/24", region2)]:
        subnet_ids.append(
            ec2_client.create_subnet(
                VpcId=vpc_id, CidrBlock=cidr_block, AvailabilityZone=region
            )["Subnet"]["SubnetId"]
        )
    return subnet_ids


def create_test_directory(ds_client, ec2_client, vpc_settings=None, tags=None):
    """Return ID of a newly created valid directory."""
    if not vpc_settings:
        good_vpc_id = create_vpc(ec2_client)
        good_subnet_ids = create_subnets(ec2_client, good_vpc_id)
        vpc_settings = {"VpcId": good_vpc_id, "SubnetIds": good_subnet_ids}

    if not tags:
        tags = []

    result = ds_client.create_directory(
        Name=f"test-{mock_random.get_random_hex(6)}.test",
        Password="Password4TheAges",
        Size="Large",
        VpcSettings=vpc_settings,
        Tags=tags,
    )
    return result["DirectoryId"]


@mock_aws
def test_ds_create_directory_validations():
    """Test validation errs that aren't caught by botocore."""
    client = boto3.client("ds", region_name=TEST_REGION)
    random_num = mock_random.get_random_hex(6)

    # Verify ValidationException error messages are accumulated properly.
    bad_name = f"bad_name_{random_num}"
    bad_password = "bad_password"
    bad_size = "big"
    ok_vpc_settings = {
        "VpcId": f"vpc-{random_num}",
        "SubnetIds": [f"subnet-{random_num}01", f"subnet-{random_num}02"],
    }
    with pytest.raises(ClientError) as exc:
        client.create_directory(
            Name=bad_name,
            Password=bad_password,
            Size=bad_size,
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
        f"Value '{bad_size}' at 'size' failed to satisfy constraint: "
        f"Member must satisfy enum value set: [Small, Large];" in err["Message"]
    )
    assert (
        rf"Value '{bad_name}' at 'name' failed to satisfy constraint: "
        rf"Member must satisfy regular expression pattern: "
        rf"^([a-zA-Z0-9]+[\.-])+([a-zA-Z0-9])+$" in err["Message"]
    )

    too_long = (
        "Test of directory service 0123456789 0123456789 0123456789 "
        "0123456789 0123456789 0123456789 0123456789 0123456789 0123456789 "
        "0123456789 0123456789"
    )
    short_name = "a:b.c"
    with pytest.raises(ClientError) as exc:
        client.create_directory(
            Name=f"test{random_num}.test",
            Password="TESTfoobar1",
            Size="Large",
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
        client.create_directory(
            Name=f"test{random_num}.test",
            Password="TESTfoobar1",
            Size="Large",
            VpcSettings=bad_vpc_settings,
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert "1 validation error detected" in err["Message"]
    assert (
        rf"Value '['{bad_vpc_settings['SubnetIds'][0]}']' at "
        rf"'vpcSettings.subnetIds' failed to satisfy constraint: "
        rf"Member must satisfy regular expression pattern: "
        rf"^(subnet-[0-9a-f]{{8}}|subnet-[0-9a-f]{{17}})$" in err["Message"]
    )


@mock_aws
def test_ds_create_directory_bad_vpc_settings():
    """Test validation of bad vpc that doesn't raise ValidationException."""
    client = boto3.client("ds", region_name=TEST_REGION)

    # Error if no VpcSettings argument.
    with pytest.raises(ClientError) as exc:
        client.create_directory(
            Name=f"test-{mock_random.get_random_hex(6)}.test",
            Password="TESTfoobar1",
            Size="Small",
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterException"
    assert "VpcSettings must be specified" in err["Message"]

    # Error if VPC is bogus.
    ec2_client = boto3.client("ec2", region_name=TEST_REGION)
    good_subnet_ids = create_subnets(ec2_client, create_vpc(ec2_client))
    with pytest.raises(ClientError) as exc:
        create_test_directory(
            client, ec2_client, {"VpcId": "vpc-12345678", "SubnetIds": good_subnet_ids}
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ClientException"
    assert "Invalid VPC ID" in err["Message"]


@mock_aws
def test_ds_create_directory_bad_subnets():
    """Test validation of VPC subnets."""
    client = boto3.client("ds", region_name=TEST_REGION)
    ec2_client = boto3.client("ec2", region_name=TEST_REGION)

    # Error if VPC subnets are bogus.
    good_vpc_id = create_vpc(ec2_client)
    with pytest.raises(ClientError) as exc:
        create_test_directory(
            client,
            ec2_client,
            {"VpcId": good_vpc_id, "SubnetIds": ["subnet-12345678", "subnet-87654321"]},
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterException"
    assert (
        "Invalid subnet ID(s). They must correspond to two subnets in "
        "different Availability Zones."
    ) in err["Message"]

    # Error if both VPC subnets are in the same region.
    subnets_same_region = create_subnets(
        ec2_client, good_vpc_id, region1=TEST_REGION + "a", region2=TEST_REGION + "a"
    )
    with pytest.raises(ClientError) as exc:
        create_test_directory(
            client, ec2_client, {"VpcId": good_vpc_id, "SubnetIds": subnets_same_region}
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ClientException"
    assert (
        "Invalid subnet ID(s). The two subnets must be in different "
        "Availability Zones."
    ) in err["Message"]
    ec2_client.delete_subnet(SubnetId=subnets_same_region[0])
    ec2_client.delete_subnet(SubnetId=subnets_same_region[1])

    # Error if only one VPC subnet.
    good_subnet_ids = create_subnets(ec2_client, good_vpc_id)
    with pytest.raises(ClientError) as exc:
        create_test_directory(
            client,
            ec2_client,
            {"VpcId": good_vpc_id, "SubnetIds": [good_subnet_ids[0]]},
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterException"
    assert "Invalid subnet ID(s). They must correspond to two subnets" in err["Message"]


@mock_aws
def test_ds_create_directory_good_args():
    """Test creation of AD directory using good arguments."""
    client = boto3.client("ds", region_name=TEST_REGION)
    ec2_client = boto3.client("ec2", region_name=TEST_REGION)

    # Verify a good call to create_directory()
    directory_id = create_test_directory(client, ec2_client)
    assert directory_id.startswith("d-")

    # Verify that too many directories can't be created.
    limits = client.get_directory_limits()["DirectoryLimits"]
    for _ in range(limits["CloudOnlyDirectoriesLimit"]):
        create_test_directory(client, ec2_client)
    with pytest.raises(ClientError) as exc:
        create_test_directory(client, ec2_client)
    err = exc.value.response["Error"]
    assert err["Code"] == "DirectoryLimitExceededException"
    assert (
        f"Directory limit exceeded. A maximum of "
        f"{limits['CloudOnlyDirectoriesLimit']} "
        f"directories may be created" in err["Message"]
    )
