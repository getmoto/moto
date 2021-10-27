"""Directory-related unit tests for Directory Services."""
import boto3
from botocore.exceptions import ClientError
import pytest

from moto import mock_ds
from moto import settings
from moto.core.utils import get_random_hex
from moto.ec2 import mock_ec2

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
                VpcId=vpc_id, CidrBlock=cidr_block, AvailabilityZone=region,
            )["Subnet"]["SubnetId"]
        )
    return subnet_ids


@mock_ds
def test_ds_create_directory_validations():
    """Test validation errs that aren't caught by botocore."""
    client = boto3.client("ds", region_name=TEST_REGION)
    random_num = get_random_hex(6)

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
        r"(?=^.{8,64}$)((?=.*\d)(?=.*[A-Z])(?=.*[a-z])|"
        r"(?=.*\d)(?=.*[^A-Za-z0-9\s])(?=.*[a-z])|"
        r"(?=.*[^A-Za-z0-9\s])(?=.*[A-Z])(?=.*[a-z])|"
        r"(?=.*\d)(?=.*[A-Z])(?=.*[^A-Za-z0-9\s]))^.*;" in err["Message"]
    )
    assert (
        f"Value '{bad_size}' at 'size' failed to satisfy constraint: "
        f"Member must satisfy enum value set: [Small, Large];" in err["Message"]
    )
    assert (
        fr"Value '{bad_name}' at 'name' failed to satisfy constraint: "
        fr"Member must satisfy regular expression pattern: "
        fr"^([a-zA-Z0-9]+[\.-])+([a-zA-Z0-9])+$" in err["Message"]
    )

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
        fr"Value '{bad_vpc_settings['SubnetIds'][0]}' at "
        fr"'vpcSettings.subnetIds' failed to satisfy constraint: "
        fr"Member must satisfy regular expression pattern: "
        fr"^(subnet-[0-9a-f]{{8}}|subnet-[0-9a-f]{{17}})$" in err["Message"]
    )


@mock_ec2
@mock_ds
def test_ds_create_directory_bad_vpc_settings():
    """Test validation of bad vpc that doesn't raise ValidationException."""
    client = boto3.client("ds", region_name=TEST_REGION)
    random_num = get_random_hex(6)
    good_name = f"test-{random_num}.test"
    good_size = "Large"
    good_passwd = "TESTfoobar1"

    # Error if no VpcSettings argument.
    with pytest.raises(ClientError) as exc:
        client.create_directory(Name=good_name, Password=good_passwd, Size=good_size)
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterException"
    assert "VpcSettings must be specified" in err["Message"]

    # Error if VPC is bogus.
    ec2_client = boto3.client("ec2", region_name=TEST_REGION)
    good_vpc_id = create_vpc(ec2_client)
    good_subnet_ids = create_subnets(ec2_client, good_vpc_id)
    with pytest.raises(ClientError) as exc:
        client.create_directory(
            Name=good_name,
            Password=good_passwd,
            Size=good_size,
            VpcSettings={"VpcId": "vpc-12345678", "SubnetIds": good_subnet_ids},
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ClientException"
    assert "Invalid VPC ID" in err["Message"]


@mock_ec2
@mock_ds
def test_ds_create_directory_bad_subnets():
    """Test validation of VPC subnets."""
    client = boto3.client("ds", region_name=TEST_REGION)
    random_num = get_random_hex(6)
    good_name = f"test-{random_num}.test"
    good_size = "Large"
    good_passwd = "TESTfoobar1"

    # Error if VPC subnets are bogus.
    ec2_client = boto3.client("ec2", region_name=TEST_REGION)
    good_vpc_id = create_vpc(ec2_client)
    # NOTE:  moto currently doesn't support EC2's describe_subnets(), so
    # the verification of subnets can't be performed.
    # with pytest.raises(ClientError) as exc:
    #     client.create_directory(
    #         Name=good_name,
    #         Password=good_passwd,
    #         Size=good_size,
    #         VpcSettings={"VpcId": good_vpc_id, "SubnetIds": ["subnet-12345678"]},
    #     )
    # err = exc.value.response["Error"]
    # assert err["Code"] == "ClientException"
    # assert "Invalid subnet ID(s)" in err["Message"]

    # Error if both VPC subnets are in the same region.
    # subnets_same_region = create_subnets(
    #     ec2_client, vpc_id, region1=TEST_REGION+"a", region2=TEST_REGION+"a"
    # )
    # with pytest.raises(ClientError) as exc:
    #     client.create_directory(
    #         Name=good_name,
    #         Password=good_passwd,
    #         Size=good_size,
    #         VpcSettings={"VpcId": "vpc-12345678", "SubnetIds": subnets_same_region},
    #     )
    # err = exc.value.response["Error"]
    # assert err["Code"] == "ClientException"
    # assert (
    #     "Invalid subnetID(s).  The two subnets must be in different Availability Zones"
    # )in err["Message"]

    # Error if only one VPC subnet.
    good_subnet_ids = create_subnets(ec2_client, good_vpc_id)
    with pytest.raises(ClientError) as exc:
        client.create_directory(
            Name=good_name,
            Password=good_passwd,
            Size=good_size,
            VpcSettings={"VpcId": good_vpc_id, "SubnetIds": [good_subnet_ids[0]]},
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterException"
    assert "Invalid subnet ID(s). They must correspond to two subnets" in err["Message"]


@mock_ec2
@mock_ds
def test_ds_create_directory_good_args():
    """Test creation of AD directory using good arguments."""
    client = boto3.client("ds", region_name=TEST_REGION)
    good_name = f"test-{get_random_hex(6)}.test"
    good_size = "Large"
    good_passwd = "TESTfoobar1"

    ec2_client = boto3.client("ec2", region_name=TEST_REGION)
    good_vpc_id = create_vpc(ec2_client)
    good_subnet_ids = create_subnets(ec2_client, good_vpc_id)

    result = client.create_directory(
        Name=good_name,
        Password=good_passwd,
        Size=good_size,
        VpcSettings={"VpcId": good_vpc_id, "SubnetIds": good_subnet_ids},
        ShortName="test",
        Description="This is a test of a good create_directory() call",
    )
    assert result["DirectoryId"].startswith("d-")
