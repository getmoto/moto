import pytest
from botocore.exceptions import ClientError

import boto3
import boto
from boto.exception import EC2ResponseError

import sure  # noqa # pylint: disable=unused-import
import random

from moto import mock_ec2, mock_ec2_deprecated
from uuid import uuid4
from .test_tags import retrieve_all_tagged

SAMPLE_DOMAIN_NAME = "example.com"
SAMPLE_NAME_SERVERS = ["10.0.0.6", "10.0.0.7"]


# Has boto3 equivalent
@mock_ec2_deprecated
def test_vpcs():
    conn = boto.connect_vpc("the_key", "the_secret")
    vpc = conn.create_vpc("10.0.0.0/16")
    vpc.cidr_block.should.equal("10.0.0.0/16")

    all_vpcs = conn.get_all_vpcs()
    all_vpcs.should.have.length_of(2)

    vpc.delete()

    all_vpcs = conn.get_all_vpcs()
    all_vpcs.should.have.length_of(1)

    with pytest.raises(EC2ResponseError) as cm:
        conn.delete_vpc("vpc-1234abcd")
    cm.value.code.should.equal("InvalidVpcID.NotFound")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none


@mock_ec2
def test_create_and_delete_vpc():
    ec2 = boto3.resource("ec2", region_name="eu-north-1")
    client = boto3.client("ec2", region_name="eu-north-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    vpc.cidr_block.should.equal("10.0.0.0/16")

    all_vpcs = retrieve_all_vpcs(client)
    [v["VpcId"] for v in all_vpcs].should.contain(vpc.id)

    vpc.delete()

    all_vpcs = retrieve_all_vpcs(client)
    [v["VpcId"] for v in all_vpcs].shouldnt.contain(vpc.id)

    with pytest.raises(ClientError) as ex:
        client.delete_vpc(VpcId="vpc-1234abcd")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal("InvalidVpcID.NotFound")


# Has boto3 equivalent
@mock_ec2_deprecated
def test_vpc_defaults():
    conn = boto.connect_vpc("the_key", "the_secret")
    vpc = conn.create_vpc("10.0.0.0/16")

    conn.get_all_vpcs().should.have.length_of(2)
    conn.get_all_route_tables().should.have.length_of(2)
    conn.get_all_security_groups(filters={"vpc-id": [vpc.id]}).should.have.length_of(1)

    vpc.delete()

    conn.get_all_vpcs().should.have.length_of(1)
    conn.get_all_route_tables().should.have.length_of(1)
    conn.get_all_security_groups(filters={"vpc-id": [vpc.id]}).should.have.length_of(0)


@mock_ec2
def test_vpc_defaults_boto3():
    ec2 = boto3.resource("ec2", region_name="eu-north-1")
    client = boto3.client("ec2", region_name="eu-north-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")

    filters = [{"Name": "vpc-id", "Values": [vpc.id]}]

    client.describe_route_tables(Filters=filters)["RouteTables"].should.have.length_of(
        1
    )
    client.describe_security_groups(Filters=filters)[
        "SecurityGroups"
    ].should.have.length_of(1)

    vpc.delete()

    client.describe_route_tables(Filters=filters)["RouteTables"].should.have.length_of(
        0
    )
    client.describe_security_groups(Filters=filters)[
        "SecurityGroups"
    ].should.have.length_of(0)


# Has boto3 equivalent
@mock_ec2_deprecated
def test_vpc_isdefault_filter():
    conn = boto.connect_vpc("the_key", "the_secret")
    vpc = conn.create_vpc("10.0.0.0/16")
    conn.get_all_vpcs(filters={"isDefault": "true"}).should.have.length_of(1)
    vpc.delete()
    conn.get_all_vpcs(filters={"isDefault": "true"}).should.have.length_of(1)


@mock_ec2
def test_vpc_isdefault_filter_boto3():
    ec2 = boto3.resource("ec2", region_name="eu-west-1")
    client = boto3.client("ec2", region_name="eu-west-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    client.describe_vpcs(Filters=[{"Name": "isDefault", "Values": ["true"]}])[
        "Vpcs"
    ].should.have.length_of(1)

    vpc.delete()

    client.describe_vpcs(Filters=[{"Name": "isDefault", "Values": ["true"]}])[
        "Vpcs"
    ].should.have.length_of(1)


# Has boto3 equivalent
@mock_ec2_deprecated
def test_multiple_vpcs_default_filter():
    conn = boto.connect_vpc("the_key", "the_secret")
    conn.create_vpc("10.8.0.0/16")
    conn.create_vpc("10.0.0.0/16")
    conn.create_vpc("192.168.0.0/16")
    conn.get_all_vpcs().should.have.length_of(4)
    vpc = conn.get_all_vpcs(filters={"isDefault": "true"})
    vpc.should.have.length_of(1)
    vpc[0].cidr_block.should.equal("172.31.0.0/16")


@mock_ec2
def test_multiple_vpcs_default_filter_boto3():
    ec2 = boto3.resource("ec2", region_name="eu-west-1")
    client = boto3.client("ec2", region_name="eu-west-1")
    ec2.create_vpc(CidrBlock="10.8.0.0/16")
    ec2.create_vpc(CidrBlock="10.0.0.0/16")
    ec2.create_vpc(CidrBlock="192.168.0.0/16")
    default_vpcs = retrieve_all_vpcs(
        client, [{"Name": "isDefault", "Values": ["true"]}]
    )
    [v["CidrBlock"] for v in default_vpcs].should.contain("172.31.0.0/16")


# Has boto3 equivalent
@mock_ec2_deprecated
def test_vpc_state_available_filter():
    conn = boto.connect_vpc("the_key", "the_secret")
    vpc = conn.create_vpc("10.0.0.0/16")
    conn.create_vpc("10.1.0.0/16")
    conn.get_all_vpcs(filters={"state": "available"}).should.have.length_of(3)
    vpc.delete()
    conn.get_all_vpcs(filters={"state": "available"}).should.have.length_of(2)


@mock_ec2
def test_vpc_state_available_filter_boto3():
    ec2 = boto3.resource("ec2", region_name="eu-west-1")
    client = boto3.client("ec2", region_name="eu-west-1")
    vpc1 = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    vpc2 = ec2.create_vpc(CidrBlock="10.1.0.0/16")

    available = retrieve_all_vpcs(client, [{"Name": "state", "Values": ["available"]}])
    [v["VpcId"] for v in available].should.contain(vpc1.id)
    [v["VpcId"] for v in available].should.contain(vpc2.id)

    vpc1.delete()

    available = retrieve_all_vpcs(client, [{"Name": "state", "Values": ["available"]}])
    [v["VpcId"] for v in available].shouldnt.contain(vpc1.id)
    [v["VpcId"] for v in available].should.contain(vpc2.id)


def retrieve_all_vpcs(client, filters=[]):  # pylint: disable=W0102
    resp = client.describe_vpcs(Filters=filters)
    all_vpcs = resp["Vpcs"]
    token = resp.get("NextToken")
    while token:
        resp = client.describe_vpcs(Filters=filters, NextToken=token)
        all_vpcs.extend(resp["Vpcs"])
        token = resp.get("NextToken")
    return all_vpcs


# Has boto3 equivalent
@mock_ec2_deprecated
def test_vpc_tagging():
    conn = boto.connect_vpc()
    vpc = conn.create_vpc("10.0.0.0/16")

    vpc.add_tag("a key", "some value")
    tag = conn.get_all_tags()[0]
    tag.name.should.equal("a key")
    tag.value.should.equal("some value")

    # Refresh the vpc
    vpc = conn.get_all_vpcs(vpc_ids=[vpc.id])[0]
    vpc.tags.should.have.length_of(1)
    vpc.tags["a key"].should.equal("some value")


@mock_ec2
def test_vpc_tagging_boto3():
    ec2 = boto3.resource("ec2", region_name="eu-west-1")
    client = boto3.client("ec2", region_name="eu-west-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")

    vpc.create_tags(Tags=[{"Key": "a key", "Value": "some value"}])

    all_tags = retrieve_all_tagged(client)
    ours = [t for t in all_tags if t["ResourceId"] == vpc.id][0]
    ours.should.have.key("Key").equal("a key")
    ours.should.have.key("Value").equal("some value")

    # Refresh the vpc
    vpc = client.describe_vpcs(VpcIds=[vpc.id])["Vpcs"][0]
    vpc["Tags"].should.equal([{"Key": "a key", "Value": "some value"}])


# Has boto3 equivalent
@mock_ec2_deprecated
def test_vpc_get_by_id():
    conn = boto.connect_vpc()
    vpc1 = conn.create_vpc("10.0.0.0/16")
    vpc2 = conn.create_vpc("10.0.0.0/16")
    conn.create_vpc("10.0.0.0/16")

    vpcs = conn.get_all_vpcs(vpc_ids=[vpc1.id, vpc2.id])
    vpcs.should.have.length_of(2)
    vpc_ids = tuple(map(lambda v: v.id, vpcs))
    vpc1.id.should.be.within(vpc_ids)
    vpc2.id.should.be.within(vpc_ids)

    with pytest.raises(EC2ResponseError) as cm:
        conn.get_all_vpcs(vpc_ids=["vpc-does_not_exist"])
    cm.value.code.should.equal("InvalidVpcID.NotFound")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none


@mock_ec2
def test_vpc_get_by_id_boto3():
    ec2 = boto3.resource("ec2", region_name="eu-west-1")
    client = boto3.client("ec2", region_name="eu-west-1")
    vpc1 = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    vpc2 = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    ec2.create_vpc(CidrBlock="10.0.0.0/16")

    vpcs = client.describe_vpcs(VpcIds=[vpc1.id, vpc2.id])["Vpcs"]
    vpcs.should.have.length_of(2)
    vpc_ids = tuple(map(lambda v: v["VpcId"], vpcs))
    vpc1.id.should.be.within(vpc_ids)
    vpc2.id.should.be.within(vpc_ids)

    with pytest.raises(ClientError) as ex:
        client.describe_vpcs(VpcIds=["vpc-does_not_exist"])
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal("InvalidVpcID.NotFound")


# Has boto3 equivalent
@mock_ec2_deprecated
def test_vpc_get_by_cidr_block():
    conn = boto.connect_vpc()
    vpc1 = conn.create_vpc("10.0.0.0/16")
    vpc2 = conn.create_vpc("10.0.0.0/16")
    conn.create_vpc("10.0.0.0/24")

    vpcs = conn.get_all_vpcs(filters={"cidr": "10.0.0.0/16"})
    vpcs.should.have.length_of(2)
    vpc_ids = tuple(map(lambda v: v.id, vpcs))
    vpc1.id.should.be.within(vpc_ids)
    vpc2.id.should.be.within(vpc_ids)


@mock_ec2
def test_vpc_get_by_cidr_block_boto3():
    ec2 = boto3.resource("ec2", region_name="eu-west-1")
    client = boto3.client("ec2", region_name="eu-west-1")
    random_ip = ".".join(map(str, (random.randint(0, 99) for _ in range(4))))
    random_cidr = f"{random_ip}/16"
    vpc1 = ec2.create_vpc(CidrBlock=random_cidr)
    vpc2 = ec2.create_vpc(CidrBlock=random_cidr)
    ec2.create_vpc(CidrBlock="10.0.0.0/24")

    vpcs = client.describe_vpcs(Filters=[{"Name": "cidr", "Values": [random_cidr]}])[
        "Vpcs"
    ]
    set([vpc["VpcId"] for vpc in vpcs]).should.equal(set([vpc1.id, vpc2.id]))


# Has boto3 equivalent
@mock_ec2_deprecated
def test_vpc_get_by_dhcp_options_id():
    conn = boto.connect_vpc()
    dhcp_options = conn.create_dhcp_options(SAMPLE_DOMAIN_NAME, SAMPLE_NAME_SERVERS)
    vpc1 = conn.create_vpc("10.0.0.0/16")
    vpc2 = conn.create_vpc("10.0.0.0/16")
    conn.create_vpc("10.0.0.0/24")

    conn.associate_dhcp_options(dhcp_options.id, vpc1.id)
    conn.associate_dhcp_options(dhcp_options.id, vpc2.id)

    vpcs = conn.get_all_vpcs(filters={"dhcp-options-id": dhcp_options.id})
    vpcs.should.have.length_of(2)
    vpc_ids = tuple(map(lambda v: v.id, vpcs))
    vpc1.id.should.be.within(vpc_ids)
    vpc2.id.should.be.within(vpc_ids)


@mock_ec2
def test_vpc_get_by_dhcp_options_id_boto3():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    client = boto3.client("ec2", region_name="us-east-1")
    dhcp_options = ec2.create_dhcp_options(
        DhcpConfigurations=[
            {"Key": "domain-name", "Values": [SAMPLE_DOMAIN_NAME]},
            {"Key": "domain-name-servers", "Values": SAMPLE_NAME_SERVERS},
        ]
    )
    vpc1 = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    vpc2 = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    ec2.create_vpc(CidrBlock="10.0.0.0/24")

    client.associate_dhcp_options(DhcpOptionsId=dhcp_options.id, VpcId=vpc1.id)
    client.associate_dhcp_options(DhcpOptionsId=dhcp_options.id, VpcId=vpc2.id)

    vpcs = client.describe_vpcs(
        Filters=[{"Name": "dhcp-options-id", "Values": [dhcp_options.id]}]
    )["Vpcs"]
    vpcs.should.have.length_of(2)
    vpc_ids = tuple(map(lambda v: v["VpcId"], vpcs))
    vpc1.id.should.be.within(vpc_ids)
    vpc2.id.should.be.within(vpc_ids)


# Has boto3 equivalent
@mock_ec2_deprecated
def test_vpc_get_by_tag():
    conn = boto.connect_vpc()
    vpc1 = conn.create_vpc("10.0.0.0/16")
    vpc2 = conn.create_vpc("10.0.0.0/16")
    vpc3 = conn.create_vpc("10.0.0.0/24")

    vpc1.add_tag("Name", "TestVPC")
    vpc2.add_tag("Name", "TestVPC")
    vpc3.add_tag("Name", "TestVPC2")

    vpcs = conn.get_all_vpcs(filters={"tag:Name": "TestVPC"})
    vpcs.should.have.length_of(2)
    vpc_ids = tuple(map(lambda v: v.id, vpcs))
    vpc1.id.should.be.within(vpc_ids)
    vpc2.id.should.be.within(vpc_ids)


@mock_ec2
def test_vpc_get_by_tag_boto3():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    client = boto3.client("ec2", region_name="us-east-1")
    vpc1 = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    vpc2 = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    vpc3 = ec2.create_vpc(CidrBlock="10.0.0.0/24")

    value1 = str(uuid4())
    vpc1.create_tags(Tags=[{"Key": "Name", "Value": value1}])
    vpc2.create_tags(Tags=[{"Key": "Name", "Value": value1}])
    vpc3.create_tags(Tags=[{"Key": "Name", "Value": "TestVPC2"}])

    vpcs = client.describe_vpcs(Filters=[{"Name": "tag:Name", "Values": [value1]}])[
        "Vpcs"
    ]
    vpcs.should.have.length_of(2)
    set([vpc["VpcId"] for vpc in vpcs]).should.equal(set([vpc1.id, vpc2.id]))


# Has boto3 equivalent
@mock_ec2_deprecated
def test_vpc_get_by_tag_key_superset():
    conn = boto.connect_vpc()
    vpc1 = conn.create_vpc("10.0.0.0/16")
    vpc2 = conn.create_vpc("10.0.0.0/16")
    vpc3 = conn.create_vpc("10.0.0.0/24")

    vpc1.add_tag("Name", "TestVPC")
    vpc1.add_tag("Key", "TestVPC2")
    vpc2.add_tag("Name", "TestVPC")
    vpc2.add_tag("Key", "TestVPC2")
    vpc3.add_tag("Key", "TestVPC2")

    vpcs = conn.get_all_vpcs(filters={"tag-key": "Name"})
    vpcs.should.have.length_of(2)
    vpc_ids = tuple(map(lambda v: v.id, vpcs))
    vpc1.id.should.be.within(vpc_ids)
    vpc2.id.should.be.within(vpc_ids)


@mock_ec2
def test_vpc_get_by_tag_key_superset_boto3():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    client = boto3.client("ec2", region_name="us-east-1")
    vpc1 = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    vpc2 = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    vpc3 = ec2.create_vpc(CidrBlock="10.0.0.0/24")

    tag_key = str(uuid4())[0:6]
    vpc1.create_tags(Tags=[{"Key": tag_key, "Value": "TestVPC"}])
    vpc1.create_tags(Tags=[{"Key": "Key", "Value": "TestVPC2"}])
    vpc2.create_tags(Tags=[{"Key": tag_key, "Value": "TestVPC"}])
    vpc2.create_tags(Tags=[{"Key": "Key", "Value": "TestVPC2"}])
    vpc3.create_tags(Tags=[{"Key": "Key", "Value": "TestVPC2"}])

    vpcs = client.describe_vpcs(Filters=[{"Name": "tag-key", "Values": [tag_key]}])[
        "Vpcs"
    ]
    vpcs.should.have.length_of(2)
    set([vpc["VpcId"] for vpc in vpcs]).should.equal(set([vpc1.id, vpc2.id]))


# Has boto3 equivalent
@mock_ec2_deprecated
def test_vpc_get_by_tag_key_subset():
    conn = boto.connect_vpc()
    vpc1 = conn.create_vpc("10.0.0.0/16")
    vpc2 = conn.create_vpc("10.0.0.0/16")
    vpc3 = conn.create_vpc("10.0.0.0/24")

    vpc1.add_tag("Name", "TestVPC")
    vpc1.add_tag("Key", "TestVPC2")
    vpc2.add_tag("Name", "TestVPC")
    vpc2.add_tag("Key", "TestVPC2")
    vpc3.add_tag("Test", "TestVPC2")

    vpcs = conn.get_all_vpcs(filters={"tag-key": ["Name", "Key"]})
    vpcs.should.have.length_of(2)
    vpc_ids = tuple(map(lambda v: v.id, vpcs))
    vpc1.id.should.be.within(vpc_ids)
    vpc2.id.should.be.within(vpc_ids)


@mock_ec2
def test_vpc_get_by_tag_key_subset_boto3():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    client = boto3.client("ec2", region_name="us-east-1")
    vpc1 = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    vpc2 = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    vpc3 = ec2.create_vpc(CidrBlock="10.0.0.0/24")

    tag_key1 = str(uuid4())[0:6]
    tag_key2 = str(uuid4())[0:6]
    vpc1.create_tags(Tags=[{"Key": tag_key1, "Value": "TestVPC"}])
    vpc1.create_tags(Tags=[{"Key": tag_key2, "Value": "TestVPC2"}])
    vpc2.create_tags(Tags=[{"Key": tag_key1, "Value": "TestVPC"}])
    vpc2.create_tags(Tags=[{"Key": tag_key2, "Value": "TestVPC2"}])
    vpc3.create_tags(Tags=[{"Key": "Test", "Value": "TestVPC2"}])

    vpcs = client.describe_vpcs(
        Filters=[{"Name": "tag-key", "Values": [tag_key1, tag_key2]}]
    )["Vpcs"]
    vpcs.should.have.length_of(2)
    set([vpc["VpcId"] for vpc in vpcs]).should.equal(set([vpc1.id, vpc2.id]))


# Has boto3 equivalent
@mock_ec2_deprecated
def test_vpc_get_by_tag_value_superset():
    conn = boto.connect_vpc()
    vpc1 = conn.create_vpc("10.0.0.0/16")
    vpc2 = conn.create_vpc("10.0.0.0/16")
    vpc3 = conn.create_vpc("10.0.0.0/24")

    vpc1.add_tag("Name", "TestVPC")
    vpc1.add_tag("Key", "TestVPC2")
    vpc2.add_tag("Name", "TestVPC")
    vpc2.add_tag("Key", "TestVPC2")
    vpc3.add_tag("Key", "TestVPC2")

    vpcs = conn.get_all_vpcs(filters={"tag-value": "TestVPC"})
    vpcs.should.have.length_of(2)
    vpc_ids = tuple(map(lambda v: v.id, vpcs))
    vpc1.id.should.be.within(vpc_ids)
    vpc2.id.should.be.within(vpc_ids)


@mock_ec2
def test_vpc_get_by_tag_value_superset_boto3():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    client = boto3.client("ec2", region_name="us-east-1")
    vpc1 = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    vpc2 = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    vpc3 = ec2.create_vpc(CidrBlock="10.0.0.0/24")

    tag_value = str(uuid4())
    vpc1.create_tags(Tags=[{"Key": "Name", "Value": tag_value}])
    vpc1.create_tags(Tags=[{"Key": "Key", "Value": "TestVPC2"}])
    vpc2.create_tags(Tags=[{"Key": "Name", "Value": tag_value}])
    vpc2.create_tags(Tags=[{"Key": "Key", "Value": "TestVPC2"}])
    vpc3.create_tags(Tags=[{"Key": "Key", "Value": "TestVPC2"}])

    vpcs = client.describe_vpcs(Filters=[{"Name": "tag-value", "Values": [tag_value]}])[
        "Vpcs"
    ]
    vpcs.should.have.length_of(2)
    set([vpc["VpcId"] for vpc in vpcs]).should.equal(set([vpc1.id, vpc2.id]))


# Has boto3 equivalent
@mock_ec2_deprecated
def test_vpc_get_by_tag_value_subset():
    conn = boto.connect_vpc()
    vpc1 = conn.create_vpc("10.0.0.0/16")
    vpc2 = conn.create_vpc("10.0.0.0/16")
    conn.create_vpc("10.0.0.0/24")

    vpc1.add_tag("Name", "TestVPC")
    vpc1.add_tag("Key", "TestVPC2")
    vpc2.add_tag("Name", "TestVPC")
    vpc2.add_tag("Key", "TestVPC2")

    vpcs = conn.get_all_vpcs(filters={"tag-value": ["TestVPC", "TestVPC2"]})
    vpcs.should.have.length_of(2)
    vpc_ids = tuple(map(lambda v: v.id, vpcs))
    vpc1.id.should.be.within(vpc_ids)
    vpc2.id.should.be.within(vpc_ids)


@mock_ec2
def test_vpc_get_by_tag_value_subset_boto3():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    client = boto3.client("ec2", region_name="us-east-1")
    vpc1 = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    vpc2 = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    ec2.create_vpc(CidrBlock="10.0.0.0/24")

    value1 = str(uuid4())[0:6]
    value2 = str(uuid4())[0:6]
    vpc1.create_tags(Tags=[{"Key": "Name", "Value": value1}])
    vpc1.create_tags(Tags=[{"Key": "Key", "Value": value2}])
    vpc2.create_tags(Tags=[{"Key": "Name", "Value": value1}])
    vpc2.create_tags(Tags=[{"Key": "Key", "Value": value2}])

    vpcs = client.describe_vpcs(
        Filters=[{"Name": "tag-value", "Values": [value1, value2]}]
    )["Vpcs"]
    vpcs.should.have.length_of(2)
    vpc_ids = tuple(map(lambda v: v["VpcId"], vpcs))
    vpc1.id.should.be.within(vpc_ids)
    vpc2.id.should.be.within(vpc_ids)


@mock_ec2
def test_default_vpc():
    ec2 = boto3.resource("ec2", region_name="us-west-1")

    # Create the default VPC
    default_vpc = list(ec2.vpcs.all())[0]
    default_vpc.cidr_block.should.equal("172.31.0.0/16")
    default_vpc.instance_tenancy.should.equal("default")
    default_vpc.reload()
    default_vpc.is_default.should.be.ok

    # Test default values for VPC attributes
    response = default_vpc.describe_attribute(Attribute="enableDnsSupport")
    attr = response.get("EnableDnsSupport")
    attr.get("Value").should.be.ok

    response = default_vpc.describe_attribute(Attribute="enableDnsHostnames")
    attr = response.get("EnableDnsHostnames")
    attr.get("Value").should.be.ok


@mock_ec2
def test_non_default_vpc():
    ec2 = boto3.resource("ec2", region_name="us-west-1")

    # Create the default VPC - this already exists when backend instantiated!
    # ec2.create_vpc(CidrBlock='172.31.0.0/16')

    # Create the non default VPC
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    vpc.reload()
    vpc.is_default.shouldnt.be.ok

    # Test default instance_tenancy
    vpc.instance_tenancy.should.equal("default")

    # Test default values for VPC attributes
    response = vpc.describe_attribute(Attribute="enableDnsSupport")
    attr = response.get("EnableDnsSupport")
    attr.get("Value").should.be.ok

    response = vpc.describe_attribute(Attribute="enableDnsHostnames")
    attr = response.get("EnableDnsHostnames")
    attr.get("Value").shouldnt.be.ok

    # Check Primary CIDR Block Associations
    cidr_block_association_set = next(iter(vpc.cidr_block_association_set), None)
    cidr_block_association_set["CidrBlockState"]["State"].should.equal("associated")
    cidr_block_association_set["CidrBlock"].should.equal(vpc.cidr_block)
    cidr_block_association_set["AssociationId"].should.contain("vpc-cidr-assoc")


@mock_ec2
def test_vpc_dedicated_tenancy():
    ec2 = boto3.resource("ec2", region_name="us-west-1")

    # Create the default VPC
    ec2.create_vpc(CidrBlock="172.31.0.0/16")

    # Create the non default VPC
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16", InstanceTenancy="dedicated")
    vpc.reload()
    vpc.is_default.shouldnt.be.ok

    vpc.instance_tenancy.should.equal("dedicated")


@mock_ec2
def test_vpc_modify_tenancy_unknown():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    ec2_client = boto3.client("ec2", region_name="us-west-1")

    # Create the default VPC
    ec2.create_vpc(CidrBlock="172.31.0.0/16")

    # Create the non default VPC
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16", InstanceTenancy="dedicated")
    vpc.instance_tenancy.should.equal("dedicated")

    with pytest.raises(ClientError) as ex:
        ec2_client.modify_vpc_tenancy(VpcId=vpc.id, InstanceTenancy="unknown")
    err = ex.value.response["Error"]
    err["Message"].should.equal("The tenancy value unknown is not supported.")
    err["Code"].should.equal("UnsupportedTenancy")

    ec2_client.modify_vpc_tenancy(VpcId=vpc.id, InstanceTenancy="default")

    vpc.reload()

    vpc.instance_tenancy.should.equal("default")


@mock_ec2
def test_vpc_modify_enable_dns_support():
    ec2 = boto3.resource("ec2", region_name="us-west-1")

    # Create the default VPC
    ec2.create_vpc(CidrBlock="172.31.0.0/16")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")

    # Test default values for VPC attributes
    response = vpc.describe_attribute(Attribute="enableDnsSupport")
    attr = response.get("EnableDnsSupport")
    attr.get("Value").should.be.ok

    vpc.modify_attribute(EnableDnsSupport={"Value": False})

    response = vpc.describe_attribute(Attribute="enableDnsSupport")
    attr = response.get("EnableDnsSupport")
    attr.get("Value").shouldnt.be.ok


@mock_ec2
def test_vpc_modify_enable_dns_hostnames():
    ec2 = boto3.resource("ec2", region_name="us-west-1")

    # Create the default VPC
    ec2.create_vpc(CidrBlock="172.31.0.0/16")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    # Test default values for VPC attributes
    response = vpc.describe_attribute(Attribute="enableDnsHostnames")
    attr = response.get("EnableDnsHostnames")
    attr.get("Value").shouldnt.be.ok

    vpc.modify_attribute(EnableDnsHostnames={"Value": True})

    response = vpc.describe_attribute(Attribute="enableDnsHostnames")
    attr = response.get("EnableDnsHostnames")
    attr.get("Value").should.be.ok


# Has boto3 equivalent
@mock_ec2_deprecated
def test_vpc_associate_dhcp_options():
    conn = boto.connect_vpc()
    dhcp_options = conn.create_dhcp_options(SAMPLE_DOMAIN_NAME, SAMPLE_NAME_SERVERS)
    vpc = conn.create_vpc("10.0.0.0/16")

    conn.associate_dhcp_options(dhcp_options.id, vpc.id)

    vpc.update()
    dhcp_options.id.should.equal(vpc.dhcp_options_id)


@mock_ec2
def test_vpc_associate_dhcp_options_boto3():
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

    vpc.reload()
    dhcp_options.id.should.equal(vpc.dhcp_options_id)


@mock_ec2
def test_associate_vpc_ipv4_cidr_block():
    ec2 = boto3.resource("ec2", region_name="us-west-1")

    vpc = ec2.create_vpc(CidrBlock="10.10.42.0/24")

    # Associate/Extend vpc CIDR range up to 5 ciders
    for i in range(43, 47):
        response = ec2.meta.client.associate_vpc_cidr_block(
            VpcId=vpc.id, CidrBlock="10.10.{}.0/24".format(i)
        )
        response["CidrBlockAssociation"]["CidrBlockState"]["State"].should.equal(
            "associating"
        )
        response["CidrBlockAssociation"]["CidrBlock"].should.equal(
            "10.10.{}.0/24".format(i)
        )
        response["CidrBlockAssociation"]["AssociationId"].should.contain(
            "vpc-cidr-assoc"
        )

    # Check all associations exist
    vpc = ec2.Vpc(vpc.id)
    vpc.cidr_block_association_set.should.have.length_of(5)
    vpc.cidr_block_association_set[2]["CidrBlockState"]["State"].should.equal(
        "associated"
    )
    vpc.cidr_block_association_set[4]["CidrBlockState"]["State"].should.equal(
        "associated"
    )

    # Check error on adding 6th association.
    with pytest.raises(ClientError) as ex:
        response = ec2.meta.client.associate_vpc_cidr_block(
            VpcId=vpc.id, CidrBlock="10.10.50.0/22"
        )
    str(ex.value).should.equal(
        "An error occurred (CidrLimitExceeded) when calling the AssociateVpcCidrBlock "
        "operation: This network '{}' has met its maximum number of allowed CIDRs: 5".format(
            vpc.id
        )
    )


@mock_ec2
def test_disassociate_vpc_ipv4_cidr_block():
    ec2 = boto3.resource("ec2", region_name="us-west-1")

    vpc = ec2.create_vpc(CidrBlock="10.10.42.0/24")
    ec2.meta.client.associate_vpc_cidr_block(VpcId=vpc.id, CidrBlock="10.10.43.0/24")

    # Remove an extended cidr block
    vpc = ec2.Vpc(vpc.id)
    non_default_assoc_cidr_block = next(
        iter(
            [
                x
                for x in vpc.cidr_block_association_set
                if vpc.cidr_block != x["CidrBlock"]
            ]
        ),
        None,
    )
    response = ec2.meta.client.disassociate_vpc_cidr_block(
        AssociationId=non_default_assoc_cidr_block["AssociationId"]
    )
    response["CidrBlockAssociation"]["CidrBlockState"]["State"].should.equal(
        "disassociating"
    )
    response["CidrBlockAssociation"]["CidrBlock"].should.equal(
        non_default_assoc_cidr_block["CidrBlock"]
    )
    response["CidrBlockAssociation"]["AssociationId"].should.equal(
        non_default_assoc_cidr_block["AssociationId"]
    )

    # Error attempting to delete a non-existent CIDR_BLOCK association
    with pytest.raises(ClientError) as ex:
        response = ec2.meta.client.disassociate_vpc_cidr_block(
            AssociationId="vpc-cidr-assoc-BORING123"
        )
    str(ex.value).should.equal(
        "An error occurred (InvalidVpcCidrBlockAssociationIdError.NotFound) when calling the "
        "DisassociateVpcCidrBlock operation: The vpc CIDR block association ID "
        "'vpc-cidr-assoc-BORING123' does not exist"
    )

    # Error attempting to delete Primary CIDR BLOCK association
    vpc_base_cidr_assoc_id = next(
        iter(
            [
                x
                for x in vpc.cidr_block_association_set
                if vpc.cidr_block == x["CidrBlock"]
            ]
        ),
        {},
    )["AssociationId"]

    with pytest.raises(ClientError) as ex:
        response = ec2.meta.client.disassociate_vpc_cidr_block(
            AssociationId=vpc_base_cidr_assoc_id
        )
    str(ex.value).should.equal(
        "An error occurred (OperationNotPermitted) when calling the DisassociateVpcCidrBlock operation: "
        "The vpc CIDR block with association ID {} may not be disassociated. It is the primary "
        "IPv4 CIDR block of the VPC".format(vpc_base_cidr_assoc_id)
    )


@mock_ec2
def test_cidr_block_association_filters():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    vpc1 = ec2.create_vpc(CidrBlock="10.90.0.0/16")
    vpc2 = ec2.create_vpc(CidrBlock="10.91.0.0/16")
    ec2.meta.client.associate_vpc_cidr_block(VpcId=vpc2.id, CidrBlock="10.10.0.0/19")
    vpc3 = ec2.create_vpc(CidrBlock="10.92.0.0/24")
    ec2.meta.client.associate_vpc_cidr_block(VpcId=vpc3.id, CidrBlock="10.92.1.0/24")
    ec2.meta.client.associate_vpc_cidr_block(VpcId=vpc3.id, CidrBlock="10.92.2.0/24")
    vpc3_assoc_response = ec2.meta.client.associate_vpc_cidr_block(
        VpcId=vpc3.id, CidrBlock="10.92.3.0/24"
    )

    # Test filters for a cidr-block in all VPCs cidr-block-associations
    filtered_vpcs = list(
        ec2.vpcs.filter(
            Filters=[
                {
                    "Name": "cidr-block-association.cidr-block",
                    "Values": ["10.10.0.0/19"],
                }
            ]
        )
    )
    [vpc.id for vpc in filtered_vpcs].shouldnt.contain(vpc1.id)
    [vpc.id for vpc in filtered_vpcs].should.contain(vpc2.id)
    [vpc.id for vpc in filtered_vpcs].shouldnt.contain(vpc3.id)

    # Test filter for association id in VPCs
    association_id = vpc3_assoc_response["CidrBlockAssociation"]["AssociationId"]
    filtered_vpcs = list(
        ec2.vpcs.filter(
            Filters=[
                {
                    "Name": "cidr-block-association.association-id",
                    "Values": [association_id],
                }
            ]
        )
    )
    filtered_vpcs.should.be.length_of(1)
    filtered_vpcs[0].id.should.equal(vpc3.id)

    # Test filter for association state in VPC - this will never show anything in this test
    filtered_vpcs = list(
        ec2.vpcs.filter(
            Filters=[
                {"Name": "cidr-block-association.association-id", "Values": ["failing"]}
            ]
        )
    )
    filtered_vpcs.should.be.length_of(0)


@mock_ec2
def test_vpc_associate_ipv6_cidr_block():
    ec2 = boto3.resource("ec2", region_name="us-west-1")

    # Test create VPC with IPV6 cidr range
    vpc = ec2.create_vpc(CidrBlock="10.10.42.0/24", AmazonProvidedIpv6CidrBlock=True)
    ipv6_cidr_block_association_set = next(
        iter(vpc.ipv6_cidr_block_association_set), None
    )
    ipv6_cidr_block_association_set["Ipv6CidrBlockState"]["State"].should.equal(
        "associated"
    )
    ipv6_cidr_block_association_set["Ipv6CidrBlock"].should.contain("::/56")
    ipv6_cidr_block_association_set["AssociationId"].should.contain("vpc-cidr-assoc")

    # Test Fail on adding 2nd IPV6 association - AWS only allows 1 at this time!
    with pytest.raises(ClientError) as ex:
        response = ec2.meta.client.associate_vpc_cidr_block(
            VpcId=vpc.id, AmazonProvidedIpv6CidrBlock=True
        )
    str(ex.value).should.equal(
        "An error occurred (CidrLimitExceeded) when calling the AssociateVpcCidrBlock "
        "operation: This network '{}' has met its maximum number of allowed CIDRs: 1".format(
            vpc.id
        )
    )

    # Test associate ipv6 cidr block after vpc created
    vpc = ec2.create_vpc(CidrBlock="10.10.50.0/24")
    response = ec2.meta.client.associate_vpc_cidr_block(
        VpcId=vpc.id, AmazonProvidedIpv6CidrBlock=True
    )
    response["Ipv6CidrBlockAssociation"]["Ipv6CidrBlockState"]["State"].should.equal(
        "associating"
    )
    response["Ipv6CidrBlockAssociation"]["Ipv6CidrBlock"].should.contain("::/56")
    response["Ipv6CidrBlockAssociation"]["AssociationId"].should.contain(
        "vpc-cidr-assoc-"
    )

    # Check on describe vpc that has ipv6 cidr block association
    vpc = ec2.Vpc(vpc.id)
    vpc.ipv6_cidr_block_association_set.should.be.length_of(1)


@mock_ec2
def test_vpc_disassociate_ipv6_cidr_block():
    ec2 = boto3.resource("ec2", region_name="us-west-1")

    # Test create VPC with IPV6 cidr range
    vpc = ec2.create_vpc(CidrBlock="10.10.42.0/24", AmazonProvidedIpv6CidrBlock=True)
    # Test disassociating the only IPV6
    assoc_id = vpc.ipv6_cidr_block_association_set[0]["AssociationId"]
    response = ec2.meta.client.disassociate_vpc_cidr_block(AssociationId=assoc_id)
    response["Ipv6CidrBlockAssociation"]["Ipv6CidrBlockState"]["State"].should.equal(
        "disassociating"
    )
    response["Ipv6CidrBlockAssociation"]["Ipv6CidrBlock"].should.contain("::/56")
    response["Ipv6CidrBlockAssociation"]["AssociationId"].should.equal(assoc_id)


@mock_ec2
def test_ipv6_cidr_block_association_filters():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    vpc1 = ec2.create_vpc(CidrBlock="10.90.0.0/16")

    vpc2 = ec2.create_vpc(CidrBlock="10.91.0.0/16", AmazonProvidedIpv6CidrBlock=True)
    vpc2_assoc_ipv6_assoc_id = vpc2.ipv6_cidr_block_association_set[0]["AssociationId"]
    ec2.meta.client.associate_vpc_cidr_block(VpcId=vpc2.id, CidrBlock="10.10.0.0/19")

    vpc3 = ec2.create_vpc(CidrBlock="10.92.0.0/24")
    ec2.meta.client.associate_vpc_cidr_block(VpcId=vpc3.id, CidrBlock="10.92.1.0/24")
    ec2.meta.client.associate_vpc_cidr_block(VpcId=vpc3.id, CidrBlock="10.92.2.0/24")
    response = ec2.meta.client.associate_vpc_cidr_block(
        VpcId=vpc3.id, AmazonProvidedIpv6CidrBlock=True
    )
    vpc3_ipv6_cidr_block = response["Ipv6CidrBlockAssociation"]["Ipv6CidrBlock"]

    vpc4 = ec2.create_vpc(CidrBlock="10.95.0.0/16")  # Here for its looks

    # Test filters for an ipv6 cidr-block in all VPCs cidr-block-associations
    filtered_vpcs = list(
        ec2.vpcs.filter(
            Filters=[
                {
                    "Name": "ipv6-cidr-block-association.ipv6-cidr-block",
                    "Values": [vpc3_ipv6_cidr_block],
                }
            ]
        )
    )
    filtered_vpcs.should.be.length_of(1)
    filtered_vpcs[0].id.should.equal(vpc3.id)

    # Test filter for association id in VPCs
    filtered_vpcs = list(
        ec2.vpcs.filter(
            Filters=[
                {
                    "Name": "ipv6-cidr-block-association.association-id",
                    "Values": [vpc2_assoc_ipv6_assoc_id],
                }
            ]
        )
    )
    filtered_vpcs.should.be.length_of(1)
    filtered_vpcs[0].id.should.equal(vpc2.id)

    # Test filter for association state in VPC - this will never show anything in this test
    assoc_vpcs = [
        vpc.id
        for vpc in ec2.vpcs.filter(
            Filters=[
                {"Name": "ipv6-cidr-block-association.state", "Values": ["associated"]}
            ]
        )
    ]
    assoc_vpcs.shouldnt.contain(vpc1.id)
    assoc_vpcs.should.contain(vpc2.id)
    assoc_vpcs.should.contain(vpc3.id)
    assoc_vpcs.shouldnt.contain(vpc4.id)


@mock_ec2
def test_create_vpc_with_invalid_cidr_block_parameter():
    ec2 = boto3.resource("ec2", region_name="us-west-1")

    vpc_cidr_block = "1000.1.0.0/20"
    with pytest.raises(ClientError) as ex:
        ec2.create_vpc(CidrBlock=vpc_cidr_block)
    str(ex.value).should.equal(
        "An error occurred (InvalidParameterValue) when calling the CreateVpc "
        "operation: Value ({}) for parameter cidrBlock is invalid. This is not a valid CIDR block.".format(
            vpc_cidr_block
        )
    )


@mock_ec2
def test_create_vpc_with_invalid_cidr_range():
    ec2 = boto3.resource("ec2", region_name="us-west-1")

    vpc_cidr_block = "10.1.0.0/29"
    with pytest.raises(ClientError) as ex:
        ec2.create_vpc(CidrBlock=vpc_cidr_block)
    str(ex.value).should.equal(
        "An error occurred (InvalidVpc.Range) when calling the CreateVpc "
        "operation: The CIDR '{}' is invalid.".format(vpc_cidr_block)
    )


@mock_ec2
def test_create_vpc_with_tags():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    # Create VPC
    vpc = ec2.create_vpc(
        CidrBlock="10.0.0.0/16",
        TagSpecifications=[
            {"ResourceType": "vpc", "Tags": [{"Key": "name", "Value": "some-vpc"}]}
        ],
    )
    assert vpc.tags == [{"Key": "name", "Value": "some-vpc"}]


@mock_ec2
def test_enable_vpc_classic_link():
    ec2 = boto3.resource("ec2", region_name="us-west-1")

    # Create VPC
    vpc = ec2.create_vpc(CidrBlock="10.1.0.0/16")

    response = ec2.meta.client.enable_vpc_classic_link(VpcId=vpc.id)
    assert response.get("Return").should.be.true


@mock_ec2
def test_enable_vpc_classic_link_failure():
    ec2 = boto3.resource("ec2", region_name="us-west-1")

    # Create VPC
    vpc = ec2.create_vpc(CidrBlock="10.90.0.0/16")

    response = ec2.meta.client.enable_vpc_classic_link(VpcId=vpc.id)
    assert response.get("Return").should.be.false


@mock_ec2
def test_disable_vpc_classic_link():
    ec2 = boto3.resource("ec2", region_name="us-west-1")

    # Create VPC
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")

    ec2.meta.client.enable_vpc_classic_link(VpcId=vpc.id)
    response = ec2.meta.client.disable_vpc_classic_link(VpcId=vpc.id)
    assert response.get("Return").should.be.false


@mock_ec2
def test_describe_classic_link_enabled():
    ec2 = boto3.resource("ec2", region_name="us-west-1")

    # Create VPC
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")

    ec2.meta.client.enable_vpc_classic_link(VpcId=vpc.id)
    response = ec2.meta.client.describe_vpc_classic_link(VpcIds=[vpc.id])
    assert response.get("Vpcs")[0].get("ClassicLinkEnabled").should.be.true


@mock_ec2
def test_describe_classic_link_disabled():
    ec2 = boto3.resource("ec2", region_name="us-west-1")

    # Create VPC
    vpc = ec2.create_vpc(CidrBlock="10.90.0.0/16")

    response = ec2.meta.client.describe_vpc_classic_link(VpcIds=[vpc.id])
    assert response.get("Vpcs")[0].get("ClassicLinkEnabled").should.be.false


@mock_ec2
def test_describe_classic_link_multiple():
    ec2 = boto3.resource("ec2", region_name="us-west-1")

    # Create VPC
    vpc1 = ec2.create_vpc(CidrBlock="10.90.0.0/16")
    vpc2 = ec2.create_vpc(CidrBlock="10.0.0.0/16")

    ec2.meta.client.enable_vpc_classic_link(VpcId=vpc2.id)
    response = ec2.meta.client.describe_vpc_classic_link(VpcIds=[vpc1.id, vpc2.id])
    expected = [
        {"VpcId": vpc1.id, "ClassicLinkDnsSupported": False},
        {"VpcId": vpc2.id, "ClassicLinkDnsSupported": True},
    ]

    # Ensure response is sorted, because they can come in random order
    assert response.get("Vpcs").sort(key=lambda x: x["VpcId"]) == expected.sort(
        key=lambda x: x["VpcId"]
    )


@mock_ec2
def test_enable_vpc_classic_link_dns_support():
    ec2 = boto3.resource("ec2", region_name="us-west-1")

    # Create VPC
    vpc = ec2.create_vpc(CidrBlock="10.1.0.0/16")

    response = ec2.meta.client.enable_vpc_classic_link_dns_support(VpcId=vpc.id)
    assert response.get("Return").should.be.true


@mock_ec2
def test_disable_vpc_classic_link_dns_support():
    ec2 = boto3.resource("ec2", region_name="us-west-1")

    # Create VPC
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")

    ec2.meta.client.enable_vpc_classic_link_dns_support(VpcId=vpc.id)
    response = ec2.meta.client.disable_vpc_classic_link_dns_support(VpcId=vpc.id)
    assert response.get("Return").should.be.false


@mock_ec2
def test_describe_classic_link_dns_support_enabled():
    ec2 = boto3.resource("ec2", region_name="us-west-1")

    # Create VPC
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")

    ec2.meta.client.enable_vpc_classic_link_dns_support(VpcId=vpc.id)
    response = ec2.meta.client.describe_vpc_classic_link_dns_support(VpcIds=[vpc.id])
    assert response.get("Vpcs")[0].get("ClassicLinkDnsSupported").should.be.true


@mock_ec2
def test_describe_classic_link_dns_support_disabled():
    ec2 = boto3.resource("ec2", region_name="us-west-1")

    # Create VPC
    vpc = ec2.create_vpc(CidrBlock="10.90.0.0/16")

    response = ec2.meta.client.describe_vpc_classic_link_dns_support(VpcIds=[vpc.id])
    assert response.get("Vpcs")[0].get("ClassicLinkDnsSupported").should.be.false


@mock_ec2
def test_describe_classic_link_dns_support_multiple():
    ec2 = boto3.resource("ec2", region_name="us-west-1")

    # Create VPC
    vpc1 = ec2.create_vpc(CidrBlock="10.90.0.0/16")
    vpc2 = ec2.create_vpc(CidrBlock="10.0.0.0/16")

    ec2.meta.client.enable_vpc_classic_link_dns_support(VpcId=vpc2.id)
    response = ec2.meta.client.describe_vpc_classic_link_dns_support(
        VpcIds=[vpc1.id, vpc2.id]
    )
    expected = [
        {"VpcId": vpc1.id, "ClassicLinkDnsSupported": False},
        {"VpcId": vpc2.id, "ClassicLinkDnsSupported": True},
    ]

    # Ensure response is sorted, because they can come in random order
    assert response.get("Vpcs").sort(key=lambda x: x["VpcId"]) == expected.sort(
        key=lambda x: x["VpcId"]
    )


@mock_ec2
def test_describe_vpc_gateway_end_points():
    ec2 = boto3.client("ec2", region_name="us-west-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]

    route_table = ec2.create_route_table(VpcId=vpc["VpcId"])["RouteTable"]
    vpc_end_point = ec2.create_vpc_endpoint(
        VpcId=vpc["VpcId"],
        ServiceName="com.amazonaws.us-east-1.s3",
        RouteTableIds=[route_table["RouteTableId"]],
        VpcEndpointType="gateway",
    )["VpcEndpoint"]
    our_id = vpc_end_point["VpcEndpointId"]

    all_endpoints = retrieve_all_endpoints(ec2)
    [e["VpcEndpointId"] for e in all_endpoints].should.contain(our_id)
    our_endpoint = [e for e in all_endpoints if e["VpcEndpointId"] == our_id][0]
    vpc_end_point["PrivateDnsEnabled"].should.be.true
    our_endpoint["PrivateDnsEnabled"].should.be.true

    our_endpoint["VpcId"].should.equal(vpc["VpcId"])
    our_endpoint["RouteTableIds"].should.equal([route_table["RouteTableId"]])

    our_endpoint.should.have.key("VpcEndpointType").equal("gateway")
    our_endpoint.should.have.key("ServiceName").equal("com.amazonaws.us-east-1.s3")
    our_endpoint.should.have.key("State").equal("available")

    endpoint_by_id = ec2.describe_vpc_endpoints(VpcEndpointIds=[our_id])[
        "VpcEndpoints"
    ][0]
    endpoint_by_id["VpcEndpointId"].should.equal(our_id)
    endpoint_by_id["VpcId"].should.equal(vpc["VpcId"])
    endpoint_by_id["RouteTableIds"].should.equal([route_table["RouteTableId"]])
    endpoint_by_id["VpcEndpointType"].should.equal("gateway")
    endpoint_by_id["ServiceName"].should.equal("com.amazonaws.us-east-1.s3")
    endpoint_by_id["State"].should.equal("available")

    with pytest.raises(ClientError) as ex:
        ec2.describe_vpc_endpoints(VpcEndpointIds=[route_table["RouteTableId"]])
    err = ex.value.response["Error"]
    err["Code"].should.equal("InvalidVpcEndpointId.NotFound")


@mock_ec2
def test_describe_vpc_interface_end_points():
    ec2 = boto3.client("ec2", region_name="us-west-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]
    subnet = ec2.create_subnet(VpcId=vpc["VpcId"], CidrBlock="10.0.1.0/24")["Subnet"]

    route_table = ec2.create_route_table(VpcId=vpc["VpcId"])["RouteTable"]
    vpc_end_point = ec2.create_vpc_endpoint(
        VpcId=vpc["VpcId"],
        ServiceName="com.tester.my-test-endpoint",
        VpcEndpointType="interface",
        SubnetIds=[subnet["SubnetId"]],
    )["VpcEndpoint"]
    our_id = vpc_end_point["VpcEndpointId"]

    vpc_end_point["DnsEntries"].should.have.length_of(1)
    vpc_end_point["DnsEntries"][0].should.have.key("DnsName").should.match(
        r".*com\.tester\.my-test-endpoint$"
    )
    vpc_end_point["DnsEntries"][0].should.have.key("HostedZoneId")

    all_endpoints = retrieve_all_endpoints(ec2)
    [e["VpcEndpointId"] for e in all_endpoints].should.contain(our_id)
    our_endpoint = [e for e in all_endpoints if e["VpcEndpointId"] == our_id][0]
    vpc_end_point["PrivateDnsEnabled"].should.be.true
    our_endpoint["PrivateDnsEnabled"].should.be.true

    our_endpoint["VpcId"].should.equal(vpc["VpcId"])
    our_endpoint.should_not.have.key("RouteTableIds")

    our_endpoint["DnsEntries"].should.equal(vpc_end_point["DnsEntries"])

    our_endpoint.should.have.key("VpcEndpointType").equal("interface")
    our_endpoint.should.have.key("ServiceName").equal("com.tester.my-test-endpoint")
    our_endpoint.should.have.key("State").equal("available")

    endpoint_by_id = ec2.describe_vpc_endpoints(VpcEndpointIds=[our_id])[
        "VpcEndpoints"
    ][0]
    endpoint_by_id["VpcEndpointId"].should.equal(our_id)
    endpoint_by_id["VpcId"].should.equal(vpc["VpcId"])
    endpoint_by_id.should_not.have.key("RouteTableIds")
    endpoint_by_id["VpcEndpointType"].should.equal("interface")
    endpoint_by_id["ServiceName"].should.equal("com.tester.my-test-endpoint")
    endpoint_by_id["State"].should.equal("available")
    endpoint_by_id["DnsEntries"].should.equal(vpc_end_point["DnsEntries"])

    with pytest.raises(ClientError) as ex:
        ec2.describe_vpc_endpoints(VpcEndpointIds=[route_table["RouteTableId"]])
    err = ex.value.response["Error"]
    err["Code"].should.equal("InvalidVpcEndpointId.NotFound")


def retrieve_all_endpoints(ec2):
    resp = ec2.describe_vpc_endpoints()
    all_endpoints = resp["VpcEndpoints"]
    next_token = resp.get("NextToken")
    while next_token:
        resp = ec2.describe_vpc_endpoints(NextToken=next_token)
        all_endpoints.extend(resp["VpcEndpoints"])
        next_token = resp.get("NextToken")
    return all_endpoints


@mock_ec2
def test_delete_vpc_end_points():
    ec2 = boto3.client("ec2", region_name="us-west-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]

    route_table = ec2.create_route_table(VpcId=vpc["VpcId"])["RouteTable"]
    vpc_end_point1 = ec2.create_vpc_endpoint(
        VpcId=vpc["VpcId"],
        ServiceName="com.amazonaws.us-west-1.s3",
        RouteTableIds=[route_table["RouteTableId"]],
        VpcEndpointType="gateway",
    )["VpcEndpoint"]
    vpc_end_point2 = ec2.create_vpc_endpoint(
        VpcId=vpc["VpcId"],
        ServiceName="com.amazonaws.us-west-1.s3",
        RouteTableIds=[route_table["RouteTableId"]],
        VpcEndpointType="gateway",
    )["VpcEndpoint"]

    vpc_endpoints = retrieve_all_endpoints(ec2)
    all_ids = [e["VpcEndpointId"] for e in vpc_endpoints]
    all_ids.should.contain(vpc_end_point1["VpcEndpointId"])
    all_ids.should.contain(vpc_end_point2["VpcEndpointId"])

    ec2.delete_vpc_endpoints(VpcEndpointIds=[vpc_end_point1["VpcEndpointId"]])

    vpc_endpoints = retrieve_all_endpoints(ec2)
    all_ids = [e["VpcEndpointId"] for e in vpc_endpoints]
    all_ids.should.contain(vpc_end_point1["VpcEndpointId"])
    all_ids.should.contain(vpc_end_point2["VpcEndpointId"])

    ep1 = ec2.describe_vpc_endpoints(VpcEndpointIds=[vpc_end_point1["VpcEndpointId"]])[
        "VpcEndpoints"
    ][0]
    ep1["State"].should.equal("deleted")

    ep2 = ec2.describe_vpc_endpoints(VpcEndpointIds=[vpc_end_point2["VpcEndpointId"]])[
        "VpcEndpoints"
    ][0]
    ep2["State"].should.equal("available")


@mock_ec2
def test_describe_vpcs_dryrun():
    client = boto3.client("ec2", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.describe_vpcs(DryRun=True)
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the DescribeVpcs operation: Request would have succeeded, but DryRun flag is set"
    )
