from __future__ import unicode_literals
import boto
import boto3
import pytest
import sure  # noqa

from moto import mock_ec2_deprecated, mock_ec2
from botocore.exceptions import ClientError


@mock_ec2_deprecated
def test_virtual_private_gateways():
    conn = boto.connect_vpc("the_key", "the_secret")

    vpn_gateway = conn.create_vpn_gateway("ipsec.1", "us-east-1a")
    vpn_gateway.should_not.be.none
    vpn_gateway.id.should.match(r"vgw-\w+")
    vpn_gateway.type.should.equal("ipsec.1")
    vpn_gateway.state.should.equal("available")
    vpn_gateway.availability_zone.should.equal("us-east-1a")


@mock_ec2_deprecated
def test_describe_vpn_gateway():
    conn = boto.connect_vpc("the_key", "the_secret")
    vpn_gateway = conn.create_vpn_gateway("ipsec.1", "us-east-1a")

    vgws = conn.get_all_vpn_gateways()
    vgws.should.have.length_of(1)

    gateway = vgws[0]
    gateway.id.should.match(r"vgw-\w+")
    gateway.id.should.equal(vpn_gateway.id)
    vpn_gateway.type.should.equal("ipsec.1")
    vpn_gateway.state.should.equal("available")
    vpn_gateway.availability_zone.should.equal("us-east-1a")


@mock_ec2
def test_attach_unknown_vpn_gateway():
    """describe_vpn_gateways attachment.vpc-id filter"""

    ec2 = boto3.client("ec2", region_name="us-east-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]

    with pytest.raises(ClientError) as ex:
        ec2.attach_vpn_gateway(VpcId=vpc["VpcId"], VpnGatewayId="?")
    err = ex.value.response["Error"]
    err["Message"].should.equal("The virtual private gateway ID '?' does not exist")
    err["Code"].should.equal("InvalidVpnGatewayID.NotFound")


@mock_ec2
def test_delete_unknown_vpn_gateway():
    """describe_vpn_gateways attachment.vpc-id filter"""

    ec2 = boto3.client("ec2", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        ec2.delete_vpn_gateway(VpnGatewayId="?")
    err = ex.value.response["Error"]
    err["Message"].should.equal("The virtual private gateway ID '?' does not exist")
    err["Code"].should.equal("InvalidVpnGatewayID.NotFound")


@mock_ec2
def test_detach_unknown_vpn_gateway():
    """describe_vpn_gateways attachment.vpc-id filter"""

    ec2 = boto3.client("ec2", region_name="us-east-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]

    with pytest.raises(ClientError) as ex:
        ec2.detach_vpn_gateway(VpcId=vpc["VpcId"], VpnGatewayId="?")
    err = ex.value.response["Error"]
    err["Message"].should.equal("The virtual private gateway ID '?' does not exist")
    err["Code"].should.equal("InvalidVpnGatewayID.NotFound")


@mock_ec2
def test_describe_vpn_connections_attachment_vpc_id_filter():
    """describe_vpn_gateways attachment.vpc-id filter"""

    ec2 = boto3.client("ec2", region_name="us-east-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    vpc_id = vpc["Vpc"]["VpcId"]
    gateway = ec2.create_vpn_gateway(AvailabilityZone="us-east-1a", Type="ipsec.1")
    gateway_id = gateway["VpnGateway"]["VpnGatewayId"]

    ec2.attach_vpn_gateway(VpcId=vpc_id, VpnGatewayId=gateway_id)

    gateways = ec2.describe_vpn_gateways(
        Filters=[{"Name": "attachment.vpc-id", "Values": [vpc_id]}]
    )

    gateways["VpnGateways"].should.have.length_of(1)
    gateways["VpnGateways"][0]["VpnGatewayId"].should.equal(gateway_id)
    gateways["VpnGateways"][0]["VpcAttachments"].should.contain(
        {"State": "attached", "VpcId": vpc_id}
    )


@mock_ec2
def test_describe_vpn_connections_state_filter_attached():
    """describe_vpn_gateways attachment.state filter - match attached"""

    ec2 = boto3.client("ec2", region_name="us-east-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    vpc_id = vpc["Vpc"]["VpcId"]
    gateway = ec2.create_vpn_gateway(AvailabilityZone="us-east-1a", Type="ipsec.1")
    gateway_id = gateway["VpnGateway"]["VpnGatewayId"]

    ec2.attach_vpn_gateway(VpcId=vpc_id, VpnGatewayId=gateway_id)

    gateways = ec2.describe_vpn_gateways(
        Filters=[{"Name": "attachment.state", "Values": ["attached"]}]
    )

    gateways["VpnGateways"].should.have.length_of(1)
    gateways["VpnGateways"][0]["VpnGatewayId"].should.equal(gateway_id)
    gateways["VpnGateways"][0]["VpcAttachments"].should.contain(
        {"State": "attached", "VpcId": vpc_id}
    )


@mock_ec2
def test_describe_vpn_connections_state_filter_deatched():
    """describe_vpn_gateways attachment.state filter - don't match detatched"""

    ec2 = boto3.client("ec2", region_name="us-east-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    vpc_id = vpc["Vpc"]["VpcId"]
    gateway = ec2.create_vpn_gateway(AvailabilityZone="us-east-1a", Type="ipsec.1")
    gateway_id = gateway["VpnGateway"]["VpnGatewayId"]

    ec2.attach_vpn_gateway(VpcId=vpc_id, VpnGatewayId=gateway_id)

    gateways = ec2.describe_vpn_gateways(
        Filters=[{"Name": "attachment.state", "Values": ["detached"]}]
    )

    gateways["VpnGateways"].should.have.length_of(0)


@mock_ec2
def test_describe_vpn_connections_id_filter_match():
    """describe_vpn_gateways vpn-gateway-id filter - match correct id"""

    ec2 = boto3.client("ec2", region_name="us-east-1")

    gateway = ec2.create_vpn_gateway(AvailabilityZone="us-east-1a", Type="ipsec.1")
    gateway_id = gateway["VpnGateway"]["VpnGatewayId"]

    gateways = ec2.describe_vpn_gateways(
        Filters=[{"Name": "vpn-gateway-id", "Values": [gateway_id]}]
    )

    gateways["VpnGateways"].should.have.length_of(1)
    gateways["VpnGateways"][0]["VpnGatewayId"].should.equal(gateway_id)


@mock_ec2
def test_describe_vpn_connections_id_filter_miss():
    """describe_vpn_gateways vpn-gateway-id filter - don't match"""

    ec2 = boto3.client("ec2", region_name="us-east-1")

    ec2.create_vpn_gateway(AvailabilityZone="us-east-1a", Type="ipsec.1")

    gateways = ec2.describe_vpn_gateways(
        Filters=[{"Name": "vpn-gateway-id", "Values": ["unknown_gateway_id"]}]
    )

    gateways["VpnGateways"].should.have.length_of(0)


@mock_ec2
def test_describe_vpn_connections_type_filter_match():
    """describe_vpn_gateways type filter - match"""

    ec2 = boto3.client("ec2", region_name="us-east-1")

    gateway = ec2.create_vpn_gateway(AvailabilityZone="us-east-1a", Type="ipsec.1")
    gateway_id = gateway["VpnGateway"]["VpnGatewayId"]

    gateways = ec2.describe_vpn_gateways(
        Filters=[{"Name": "type", "Values": ["ipsec.1"]}]
    )

    gateways["VpnGateways"].should.have.length_of(1)
    gateways["VpnGateways"][0]["VpnGatewayId"].should.equal(gateway_id)


@mock_ec2
def test_describe_vpn_connections_type_filter_miss():
    """describe_vpn_gateways type filter - don't match"""

    ec2 = boto3.client("ec2", region_name="us-east-1")

    ec2.create_vpn_gateway(AvailabilityZone="us-east-1a", Type="ipsec.1")

    gateways = ec2.describe_vpn_gateways(
        Filters=[{"Name": "type", "Values": ["unknown_type"]}]
    )

    gateways["VpnGateways"].should.have.length_of(0)


@mock_ec2_deprecated
def test_vpn_gateway_vpc_attachment():
    conn = boto.connect_vpc("the_key", "the_secret")
    vpc = conn.create_vpc("10.0.0.0/16")
    vpn_gateway = conn.create_vpn_gateway("ipsec.1", "us-east-1a")

    conn.attach_vpn_gateway(vpn_gateway_id=vpn_gateway.id, vpc_id=vpc.id)

    gateway = conn.get_all_vpn_gateways()[0]
    attachments = gateway.attachments
    attachments.should.have.length_of(1)
    attachments[0].vpc_id.should.equal(vpc.id)
    attachments[0].state.should.equal("attached")


@mock_ec2_deprecated
def test_delete_vpn_gateway():
    conn = boto.connect_vpc("the_key", "the_secret")
    vpn_gateway = conn.create_vpn_gateway("ipsec.1", "us-east-1a")

    conn.delete_vpn_gateway(vpn_gateway.id)
    vgws = conn.get_all_vpn_gateways()
    vgws.should.have.length_of(0)


@mock_ec2_deprecated
def test_vpn_gateway_tagging():
    conn = boto.connect_vpc("the_key", "the_secret")
    vpn_gateway = conn.create_vpn_gateway("ipsec.1", "us-east-1a")
    vpn_gateway.add_tag("a key", "some value")

    tag = conn.get_all_tags()[0]
    tag.name.should.equal("a key")
    tag.value.should.equal("some value")

    # Refresh the subnet
    vpn_gateway = conn.get_all_vpn_gateways()[0]
    vpn_gateway.tags.should.have.length_of(1)
    vpn_gateway.tags["a key"].should.equal("some value")


@mock_ec2_deprecated
def test_detach_vpn_gateway():

    conn = boto.connect_vpc("the_key", "the_secret")
    vpc = conn.create_vpc("10.0.0.0/16")
    vpn_gateway = conn.create_vpn_gateway("ipsec.1", "us-east-1a")

    conn.attach_vpn_gateway(vpn_gateway_id=vpn_gateway.id, vpc_id=vpc.id)

    gateway = conn.get_all_vpn_gateways()[0]
    attachments = gateway.attachments
    attachments.should.have.length_of(1)
    attachments[0].vpc_id.should.equal(vpc.id)
    attachments[0].state.should.equal("attached")

    conn.detach_vpn_gateway(vpn_gateway_id=vpn_gateway.id, vpc_id=vpc.id)

    gateway = conn.get_all_vpn_gateways()[0]
    attachments = gateway.attachments
    attachments.should.have.length_of(0)
