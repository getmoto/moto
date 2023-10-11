import pytest

import boto3
from botocore.exceptions import ClientError

import random
import uuid

from moto import mock_ec2, settings
from unittest import SkipTest

SAMPLE_DOMAIN_NAME = "example.com"
SAMPLE_NAME_SERVERS = ["10.0.0.6", "10.0.0.7"]


@mock_ec2
def test_dhcp_options_associate():
    """associate dhcp option"""
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")

    dhcp_options = ec2.create_dhcp_options(
        DhcpConfigurations=[
            {"Key": "domain-name", "Values": [SAMPLE_DOMAIN_NAME]},
            {"Key": "domain-name-servers", "Values": SAMPLE_NAME_SERVERS},
        ]
    )
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")

    client.associate_dhcp_options(DhcpOptionsId=dhcp_options.id, VpcId=vpc.id)
    #
    vpc.reload()
    assert vpc.dhcp_options_id == dhcp_options.id


@mock_ec2
def test_dhcp_options_associate_invalid_dhcp_id():
    """associate dhcp option bad dhcp options id"""
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")

    with pytest.raises(ClientError) as ex:
        client.associate_dhcp_options(DhcpOptionsId="foo", VpcId=vpc.id)
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "InvalidDhcpOptionID.NotFound"


@mock_ec2
def test_dhcp_options_associate_invalid_vpc_id():
    """associate dhcp option invalid vpc id"""
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")
    dhcp_options = ec2.create_dhcp_options(
        DhcpConfigurations=[
            {"Key": "domain-name", "Values": [SAMPLE_DOMAIN_NAME]},
            {"Key": "domain-name-servers", "Values": SAMPLE_NAME_SERVERS},
        ]
    )

    with pytest.raises(ClientError) as ex:
        client.associate_dhcp_options(DhcpOptionsId=dhcp_options.id, VpcId="foo")
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "InvalidVpcID.NotFound"


@mock_ec2
def test_dhcp_options_disassociation():
    """Ensure that VPCs can be set to the 'default' DHCP options set for disassociation."""
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")
    dhcp_options = ec2.create_dhcp_options(
        DhcpConfigurations=[
            {"Key": "domain-name", "Values": [SAMPLE_DOMAIN_NAME]},
            {"Key": "domain-name-servers", "Values": SAMPLE_NAME_SERVERS},
        ]
    )
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")

    # Ensure newly created VPCs without any DHCP options can be disassociated
    client.associate_dhcp_options(DhcpOptionsId="default", VpcId=vpc.id)
    vpc.reload()
    assert vpc.dhcp_options_id == "default"

    client.associate_dhcp_options(DhcpOptionsId=dhcp_options.id, VpcId=vpc.id)
    vpc.reload()
    assert vpc.dhcp_options_id == dhcp_options.id

    # Ensure VPCs with already associated DHCP options can be disassociated
    client.associate_dhcp_options(DhcpOptionsId="default", VpcId=vpc.id)
    vpc.reload()
    assert vpc.dhcp_options_id == "default"


@mock_ec2
def test_dhcp_options_delete_with_vpc():
    """Test deletion of dhcp options with vpc"""
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")
    dhcp_options = ec2.create_dhcp_options(
        DhcpConfigurations=[
            {"Key": "domain-name", "Values": [SAMPLE_DOMAIN_NAME]},
            {"Key": "domain-name-servers", "Values": SAMPLE_NAME_SERVERS},
        ]
    )
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")

    client.associate_dhcp_options(DhcpOptionsId=dhcp_options.id, VpcId=vpc.id)

    with pytest.raises(ClientError) as ex:
        client.delete_dhcp_options(DhcpOptionsId=dhcp_options.id)
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "DependencyViolation"

    vpc.delete()

    with pytest.raises(ClientError) as ex:
        client.describe_dhcp_options(DhcpOptionsIds=[dhcp_options.id])
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "InvalidDhcpOptionID.NotFound"


@mock_ec2
def test_create_dhcp_options():
    """Create most basic dhcp option"""
    ec2 = boto3.resource("ec2", region_name="us-west-1")

    dhcp_options = ec2.create_dhcp_options(
        DhcpConfigurations=[
            {"Key": "domain-name", "Values": [SAMPLE_DOMAIN_NAME]},
            {"Key": "domain-name-servers", "Values": SAMPLE_NAME_SERVERS},
        ]
    )
    config = dhcp_options.dhcp_configurations
    assert len(config) == 2
    assert {
        "Key": "domain-name-servers",
        "Values": [{"Value": ip} for ip in SAMPLE_NAME_SERVERS],
    } in config

    assert {"Key": "domain-name", "Values": [{"Value": SAMPLE_DOMAIN_NAME}]} in config


@mock_ec2
def test_create_dhcp_options_invalid_options():
    """Create invalid dhcp options"""
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    servers = ["f", "f", "f", "f", "f"]

    with pytest.raises(ClientError) as ex:
        ec2.create_dhcp_options(
            DhcpConfigurations=[{"Key": "ntp-servers", "Values": servers}]
        )
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "InvalidParameterValue"

    with pytest.raises(ClientError) as ex:
        ec2.create_dhcp_options(
            DhcpConfigurations=[{"Key": "netbios-node-type", "Values": ["0"]}]
        )
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "InvalidParameterValue"


@mock_ec2
def test_describe_dhcp_options():
    """Test dhcp options lookup by id"""
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")

    dhcp_options = ec2.create_dhcp_options(
        DhcpConfigurations=[
            {"Key": "domain-name", "Values": [SAMPLE_DOMAIN_NAME]},
            {"Key": "domain-name-servers", "Values": SAMPLE_NAME_SERVERS},
        ]
    )
    all_options = client.describe_dhcp_options(DhcpOptionsIds=[dhcp_options.id])[
        "DhcpOptions"
    ]
    assert len(all_options) == 1

    all_options = client.describe_dhcp_options()["DhcpOptions"]
    assert len(all_options) >= 1, "Should have recently created DHCP option"
    recently_created = [
        o for o in all_options if o["DhcpOptionsId"] == dhcp_options.id
    ][0]
    assert recently_created["DhcpOptionsId"] == dhcp_options.id
    config = recently_created["DhcpConfigurations"]
    assert len(config) == 2
    assert {
        "Key": "domain-name-servers",
        "Values": [{"Value": ip} for ip in SAMPLE_NAME_SERVERS],
    } in config
    assert {"Key": "domain-name", "Values": [{"Value": SAMPLE_DOMAIN_NAME}]} in config


@mock_ec2
def test_describe_dhcp_options_invalid_id():
    """get error on invalid dhcp_option_id lookup"""
    client = boto3.client("ec2", region_name="us-west-1")

    with pytest.raises(ClientError) as ex:
        client.describe_dhcp_options(DhcpOptionsIds=["1"])
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "InvalidDhcpOptionID.NotFound"


@mock_ec2
def test_delete_dhcp_options():
    """delete dhcp option"""
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")

    dhcp_option = ec2.create_dhcp_options(
        DhcpConfigurations=[
            {"Key": "domain-name", "Values": [SAMPLE_DOMAIN_NAME]},
            {"Key": "domain-name-servers", "Values": SAMPLE_NAME_SERVERS},
        ]
    )

    client.delete_dhcp_options(DhcpOptionsId=dhcp_option.id)

    with pytest.raises(ClientError) as ex:
        client.describe_dhcp_options(DhcpOptionsIds=[dhcp_option.id])
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "InvalidDhcpOptionID.NotFound"


@mock_ec2
def test_delete_dhcp_options_invalid_id():
    client = boto3.client("ec2", region_name="us-west-1")

    with pytest.raises(ClientError) as ex:
        client.delete_dhcp_options(DhcpOptionsId="dopt-abcd1234")
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "InvalidDhcpOptionID.NotFound"


@mock_ec2
def test_delete_dhcp_options_malformed_id():
    client = boto3.client("ec2", region_name="us-west-1")

    with pytest.raises(ClientError) as ex:
        client.delete_dhcp_options(DhcpOptionsId="foo-abcd1234")
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "InvalidDhcpOptionsId.Malformed"


@mock_ec2
def test_dhcp_tagging():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")

    dhcp_option = ec2.create_dhcp_options(
        DhcpConfigurations=[
            {"Key": "domain-name", "Values": [SAMPLE_DOMAIN_NAME]},
            {"Key": "domain-name-servers", "Values": SAMPLE_NAME_SERVERS},
        ]
    )

    tag_value = str(uuid.uuid4())
    dhcp_option.create_tags(Tags=[{"Key": "a tag", "Value": tag_value}])

    tag = client.describe_tags(
        Filters=[{"Name": "resource-id", "Values": [dhcp_option.id]}]
    )["Tags"][0]
    assert tag["ResourceId"] == dhcp_option.id
    assert tag["ResourceType"] == "dhcp-options"
    assert tag["Key"] == "a tag"
    assert tag["Value"] == tag_value

    # Refresh the DHCP options
    dhcp_option = client.describe_dhcp_options(DhcpOptionsIds=[dhcp_option.id])[
        "DhcpOptions"
    ][0]
    assert dhcp_option["Tags"] == [{"Key": "a tag", "Value": tag_value}]


@mock_ec2
def test_dhcp_options_get_by_tag():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")

    dhcp_tag_value = str(uuid.uuid4())

    dhcp1 = ec2.create_dhcp_options(
        DhcpConfigurations=[
            {"Key": "domain-name", "Values": ["example.com"]},
            {"Key": "domain-name-servers", "Values": ["10.0.10.2"]},
        ]
    )
    dhcp1_tag_name = str(uuid.uuid4())
    dhcp1.create_tags(
        Tags=[
            {"Key": "Name", "Value": dhcp1_tag_name},
            {"Key": "test-tag", "Value": dhcp_tag_value},
        ]
    )

    dhcp2 = ec2.create_dhcp_options(
        DhcpConfigurations=[
            {"Key": "domain-name", "Values": ["example.com"]},
            {"Key": "domain-name-servers", "Values": ["10.0.20.2"]},
        ]
    )
    dhcp2_tag_name = str(uuid.uuid4())
    dhcp2.create_tags(
        Tags=[
            {"Key": "Name", "Value": dhcp2_tag_name},
            {"Key": "test-tag", "Value": dhcp_tag_value},
        ]
    )

    dhcp_options_sets = client.describe_dhcp_options(
        Filters=[
            {"Name": "tag:Name", "Values": [dhcp1_tag_name]},
            {"Name": "tag:test-tag", "Values": [dhcp_tag_value]},
        ]
    )["DhcpOptions"]

    assert len(dhcp_options_sets) == 1
    config = dhcp_options_sets[0]["DhcpConfigurations"]
    assert len(config) == 2
    assert {"Key": "domain-name", "Values": [{"Value": "example.com"}]} in config
    assert {"Key": "domain-name-servers", "Values": [{"Value": "10.0.10.2"}]} in config
    tags = dhcp_options_sets[0]["Tags"]
    assert len(tags) == 2
    assert {"Key": "Name", "Value": dhcp1_tag_name} in tags
    assert {"Key": "test-tag", "Value": dhcp_tag_value} in tags

    dhcp_options_sets = client.describe_dhcp_options(
        Filters=[
            {"Name": "tag:Name", "Values": [dhcp2_tag_name]},
            {"Name": "tag:test-tag", "Values": [dhcp_tag_value]},
        ]
    )["DhcpOptions"]

    assert len(dhcp_options_sets) == 1
    config = dhcp_options_sets[0]["DhcpConfigurations"]
    assert len(config) == 2
    assert {"Key": "domain-name", "Values": [{"Value": "example.com"}]} in config
    assert {"Key": "domain-name-servers", "Values": [{"Value": "10.0.20.2"}]} in config
    tags = dhcp_options_sets[0]["Tags"]
    assert len(tags) == 2
    assert {"Key": "Name", "Value": dhcp2_tag_name} in tags
    assert {"Key": "test-tag", "Value": dhcp_tag_value} in tags

    dhcp_options_sets = client.describe_dhcp_options(
        Filters=[{"Name": "tag:test-tag", "Values": [dhcp_tag_value]}]
    )["DhcpOptions"]

    assert len(dhcp_options_sets) == 2


@mock_ec2
def test_dhcp_options_get_by_id():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")

    dhcp1 = ec2.create_dhcp_options(
        DhcpConfigurations=[
            {"Key": "domain-name", "Values": ["test1.com"]},
            {"Key": "domain-name-servers", "Values": ["10.0.10.2"]},
        ]
    )
    dhcp1.create_tags(Tags=[{"Key": "Name", "Value": "TestDhcpOptions1"}])
    dhcp1.create_tags(Tags=[{"Key": "test-tag", "Value": "test-value"}])

    dhcp2 = ec2.create_dhcp_options(
        DhcpConfigurations=[
            {"Key": "domain-name", "Values": ["test2.com"]},
            {"Key": "domain-name-servers", "Values": ["10.0.20.2"]},
        ]
    )
    dhcp1.create_tags(Tags=[{"Key": "Name", "Value": "TestDhcpOptions2"}])
    dhcp1.create_tags(Tags=[{"Key": "test-tag", "Value": "test-value"}])

    options = client.describe_dhcp_options()["DhcpOptions"]
    d_ids = [d["DhcpOptionsId"] for d in options]
    assert dhcp1.id in d_ids
    assert dhcp2.id in d_ids

    d = client.describe_dhcp_options(
        Filters=[{"Name": "dhcp-options-id", "Values": [dhcp1.id]}]
    )["DhcpOptions"]

    assert len(d) == 1
    assert d[0]["DhcpOptionsId"] == dhcp1.id

    d = client.describe_dhcp_options(
        Filters=[{"Name": "dhcp-options-id", "Values": [dhcp2.id]}]
    )["DhcpOptions"]

    assert len(d) == 1
    assert d[0]["DhcpOptionsId"] == dhcp2.id


@mock_ec2
def test_dhcp_options_get_by_value_filter():
    ec2 = boto3.resource("ec2", region_name="us-west-1")

    random_server_1 = ".".join(map(str, (random.randint(0, 99) for _ in range(4))))
    random_server_2 = ".".join(map(str, (random.randint(0, 99) for _ in range(4))))
    random_server_3 = ".".join(map(str, (random.randint(0, 99) for _ in range(4))))

    ec2.create_dhcp_options(
        DhcpConfigurations=[
            {"Key": "domain-name", "Values": ["example.com"]},
            {"Key": "domain-name-servers", "Values": [random_server_1]},
        ]
    )

    ec2.create_dhcp_options(
        DhcpConfigurations=[
            {"Key": "domain-name", "Values": ["example.com"]},
            {"Key": "domain-name-servers", "Values": [random_server_2]},
        ]
    )

    ec2.create_dhcp_options(
        DhcpConfigurations=[
            {"Key": "domain-name", "Values": ["example.com"]},
            {"Key": "domain-name-servers", "Values": [random_server_3]},
        ]
    )

    filters = [{"Name": "value", "Values": [random_server_2]}]
    dhcp_options_sets = list(ec2.dhcp_options_sets.filter(Filters=filters))
    assert len(dhcp_options_sets) == 1


@mock_ec2
def test_dhcp_options_get_by_key_filter():
    ec2 = boto3.resource("ec2", region_name="us-west-1")

    random_domain_name = str(uuid.uuid4())[0:6]

    ec2.create_dhcp_options(
        DhcpConfigurations=[{"Key": "domain-name", "Values": [random_domain_name]}]
    )

    ec2.create_dhcp_options(
        DhcpConfigurations=[{"Key": "domain-name", "Values": ["example.com"]}]
    )

    ec2.create_dhcp_options(
        DhcpConfigurations=[{"Key": "domain-name", "Values": [random_domain_name]}]
    )

    filters = [{"Name": "key", "Values": ["domain-name"]}]
    dhcp_options_sets = list(ec2.dhcp_options_sets.filter(Filters=filters))
    assert (
        len(dhcp_options_sets) >= 3
    ), "Should have at least 3 DHCP options just created"

    configs = []
    for d in dhcp_options_sets:
        configs.extend(d.dhcp_configurations)

    servers = []
    for config in configs:
        if config["Key"] == "domain-name":
            servers.extend(config["Values"])
    assert {"Value": random_domain_name} in servers
    assert {"Value": "example.com"} in servers


@mock_ec2
def test_dhcp_options_get_by_invalid_filter():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Will throw a generic 500 in ServerMode")
    ec2 = boto3.resource("ec2", region_name="us-west-1")

    client = boto3.client("ec2", region_name="us-west-1")

    ec2.create_dhcp_options(
        DhcpConfigurations=[
            {"Key": "domain-name", "Values": [SAMPLE_DOMAIN_NAME]},
            {"Key": "domain-name-servers", "Values": SAMPLE_NAME_SERVERS},
        ]
    )

    filters = [{"Name": "invalid-filter", "Values": ["n/a"]}]
    with pytest.raises(NotImplementedError):
        client.describe_dhcp_options(Filters=filters)
