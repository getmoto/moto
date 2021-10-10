from __future__ import unicode_literals
import boto
import boto3
import pytest
import sure  # noqa

from moto import mock_ec2_deprecated, mock_ec2
from botocore.exceptions import ClientError
from .test_tags import retrieve_all_tagged


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


# Has boto3 equivalent
@mock_ec2_deprecated
def test_virtual_private_gateways():
    conn = boto.connect_vpc("the_key", "the_secret")

    vpn_gateway = conn.create_vpn_gateway("ipsec.1", "us-east-1a")
    vpn_gateway.should_not.be.none
    vpn_gateway.id.should.match(r"vgw-\w+")
    vpn_gateway.type.should.equal("ipsec.1")
    vpn_gateway.state.should.equal("available")
    vpn_gateway.availability_zone.should.equal("us-east-1a")


@mock_ec2
def test_virtual_private_gateways_boto3():
    client = boto3.client("ec2", region_name="us-west-1")

    vpn_gateway = client.create_vpn_gateway(
        Type="ipsec.1", AvailabilityZone="us-east-1a"
    )["VpnGateway"]

    vpn_gateway["VpnGatewayId"].should.match(r"vgw-\w+")
    vpn_gateway["Type"].should.equal("ipsec.1")
    vpn_gateway["State"].should.equal("available")
    vpn_gateway["AvailabilityZone"].should.equal("us-east-1a")


# Has boto3 equivalent
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
def test_describe_vpn_gateway_boto3():
    client = boto3.client("ec2", region_name="us-west-1")
    vpn_gateway = client.create_vpn_gateway(
        Type="ipsec.1", AvailabilityZone="us-east-1a"
    )["VpnGateway"]

    vgws = client.describe_vpn_gateways(VpnGatewayIds=[vpn_gateway["VpnGatewayId"]])[
        "VpnGateways"
    ]
    vgws.should.have.length_of(1)

    gateway = vgws[0]
    gateway["VpnGatewayId"].should.match(r"vgw-\w+")
    gateway["VpnGatewayId"].should.equal(vpn_gateway["VpnGatewayId"])
    # TODO: fixme. This currently returns the ID
    # gateway["Type"].should.equal("ipsec.1")
    gateway["State"].should.equal("available")
    gateway["AvailabilityZone"].should.equal("us-east-1a")


@mock_ec2
def test_describe_vpn_connections_state_filter_attached():
    """ describe_vpn_gateways attachment.state filter - match attached """

    ec2 = boto3.client("ec2", region_name="us-east-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    vpc_id = vpc["Vpc"]["VpcId"]
    gateway = ec2.create_vpn_gateway(AvailabilityZone="us-east-1a", Type="ipsec.1")
    gateway_id = gateway["VpnGateway"]["VpnGatewayId"]

    ec2.attach_vpn_gateway(VpcId=vpc_id, VpnGatewayId=gateway_id)

    all_gateways = retrieve_all(
        ec2, [{"Name": "attachment.state", "Values": ["attached"]}]
    )

    [gw["VpnGatewayId"] for gw in all_gateways].should.contain(gateway_id)

    my_gateway = [gw for gw in all_gateways if gw["VpnGatewayId"] == gateway_id][0]

    my_gateway["VpcAttachments"].should.contain({"State": "attached", "VpcId": vpc_id})


@mock_ec2
def test_describe_vpn_connections_id_filter_match():
    """ describe_vpn_gateways vpn-gateway-id filter - match correct id """

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
    """ describe_vpn_gateways vpn-gateway-id filter - don't match """

    ec2 = boto3.client("ec2", region_name="us-east-1")

    ec2.create_vpn_gateway(AvailabilityZone="us-east-1a", Type="ipsec.1")

    gateways = ec2.describe_vpn_gateways(
        Filters=[{"Name": "vpn-gateway-id", "Values": ["unknown_gateway_id"]}]
    )

    gateways["VpnGateways"].should.have.length_of(0)


@mock_ec2
def test_describe_vpn_connections_type_filter_match():
    """ describe_vpn_gateways type filter - match """

    ec2 = boto3.client("ec2", region_name="us-east-1")

    gateway = ec2.create_vpn_gateway(AvailabilityZone="us-east-1a", Type="ipsec.1")
    gateway_id = gateway["VpnGateway"]["VpnGatewayId"]

    my_gateways = retrieve_all(ec2, [{"Name": "type", "Values": ["ipsec.1"]}])

    [gw["VpnGatewayId"] for gw in my_gateways].should.contain(gateway_id)


@mock_ec2
def test_describe_vpn_connections_type_filter_miss():
    """ describe_vpn_gateways type filter - don't match """

    ec2 = boto3.client("ec2", region_name="us-east-1")

    ec2.create_vpn_gateway(AvailabilityZone="us-east-1a", Type="ipsec.1")

    gateways = ec2.describe_vpn_gateways(
        Filters=[{"Name": "type", "Values": ["unknown_type"]}]
    )

    gateways["VpnGateways"].should.have.length_of(0)


# Has boto3 equivalent
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


@mock_ec2
def test_vpn_gateway_vpc_attachment_boto3():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    vpn_gateway = client.create_vpn_gateway(
        Type="ipsec.1", AvailabilityZone="us-east-1a"
    )["VpnGateway"]
    vpng_id = vpn_gateway["VpnGatewayId"]

    client.attach_vpn_gateway(VpnGatewayId=vpng_id, VpcId=vpc.id)

    gateway = client.describe_vpn_gateways(VpnGatewayIds=[vpng_id])["VpnGateways"][0]
    attachments = gateway["VpcAttachments"]
    attachments.should.equal([{"State": "attached", "VpcId": vpc.id}])


# Has boto3 equivalent
@mock_ec2_deprecated
def test_delete_vpn_gateway():
    conn = boto.connect_vpc("the_key", "the_secret")
    vpn_gateway = conn.create_vpn_gateway("ipsec.1", "us-east-1a")

    conn.delete_vpn_gateway(vpn_gateway.id)
    vgws = conn.get_all_vpn_gateways()
    vgws.should.have.length_of(1)
    vgws[0].state.should.equal("deleted")


@mock_ec2
def test_delete_vpn_gateway_boto3():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")
    vpn_gateway = client.create_vpn_gateway(
        Type="ipsec.1", AvailabilityZone="us-east-1a"
    )["VpnGateway"]
    vpng_id = vpn_gateway["VpnGatewayId"]

    client.delete_vpn_gateway(VpnGatewayId=vpng_id)
    gateways = client.describe_vpn_gateways(VpnGatewayIds=[vpng_id])["VpnGateways"]
    gateways.should.have.length_of(1)
    gateways[0].should.have.key("State").equal("deleted")


# Has boto3 equivalent
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


@mock_ec2
def test_vpn_gateway_tagging_boto3():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")
    vpn_gateway = client.create_vpn_gateway(
        Type="ipsec.1", AvailabilityZone="us-east-1a"
    )["VpnGateway"]
    client.create_tags(
        Resources=[vpn_gateway["VpnGatewayId"]],
        Tags=[{"Key": "a key", "Value": "some value"}],
    )

    all_tags = retrieve_all_tagged(client)
    ours = [a for a in all_tags if a["ResourceId"] == vpn_gateway["VpnGatewayId"]][0]
    ours.should.have.key("Key").equal("a key")
    ours.should.have.key("Value").equal("some value")

    vpn_gateway = client.describe_vpn_gateways()["VpnGateways"][0]
    # TODO: Fixme: Tags is currently empty
    # vpn_gateway["Tags"].should.equal([{'Key': 'a key', 'Value': 'some value'}])


# Has boto3 equivalent
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
    attachments.should.have.length_of(1)
    attachments[0].state.should.equal("detached")


@mock_ec2
def test_detach_vpn_gateway_boto3():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    vpn_gateway = client.create_vpn_gateway(
        Type="ipsec.1", AvailabilityZone="us-east-1a"
    )
    vpn_gateway = vpn_gateway["VpnGateway"]
    vpng_id = vpn_gateway["VpnGatewayId"]

    client.attach_vpn_gateway(VpnGatewayId=vpng_id, VpcId=vpc.id)

    gateway = client.describe_vpn_gateways(VpnGatewayIds=[vpng_id])["VpnGateways"][0]
    attachments = gateway["VpcAttachments"]
    attachments.should.equal([{"State": "attached", "VpcId": vpc.id}])

    client.detach_vpn_gateway(VpnGatewayId=vpng_id, VpcId=vpc.id)

    gateway = client.describe_vpn_gateways(VpnGatewayIds=[vpng_id])["VpnGateways"][0]
    attachments = gateway["VpcAttachments"]
    attachments.should.equal([{"State": "detached", "VpcId": vpc.id}])


def retrieve_all(client, filters=[]):
    resp = client.describe_vpn_gateways(Filters=filters)
    all_gateways = resp["VpnGateways"]
    token = resp.get("NextToken")
    while token:
        resp = client.describe_vpn_gateways(Filters=filters)
        all_gateways.extend(resp["VpnGateways"])
        token = resp.get("NextToken")
    return all_gateways
