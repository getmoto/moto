import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws

from .test_tags import retrieve_all_tagged


@mock_aws
def test_attach_unknown_vpn_gateway():
    """describe_vpn_gateways attachment.vpc-id filter"""

    ec2 = boto3.client("ec2", region_name="us-east-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]

    with pytest.raises(ClientError) as ex:
        ec2.attach_vpn_gateway(VpcId=vpc["VpcId"], VpnGatewayId="?")
    err = ex.value.response["Error"]
    assert err["Message"] == "The virtual private gateway ID '?' does not exist"
    assert err["Code"] == "InvalidVpnGatewayID.NotFound"


@mock_aws
def test_delete_unknown_vpn_gateway():
    """describe_vpn_gateways attachment.vpc-id filter"""

    ec2 = boto3.client("ec2", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        ec2.delete_vpn_gateway(VpnGatewayId="?")
    err = ex.value.response["Error"]
    assert err["Message"] == "The virtual private gateway ID '?' does not exist"
    assert err["Code"] == "InvalidVpnGatewayID.NotFound"


@mock_aws
def test_detach_unknown_vpn_gateway():
    """describe_vpn_gateways attachment.vpc-id filter"""

    ec2 = boto3.client("ec2", region_name="us-east-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]

    with pytest.raises(ClientError) as ex:
        ec2.detach_vpn_gateway(VpcId=vpc["VpcId"], VpnGatewayId="?")
    err = ex.value.response["Error"]
    assert err["Message"] == "The virtual private gateway ID '?' does not exist"
    assert err["Code"] == "InvalidVpnGatewayID.NotFound"


@mock_aws
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

    assert len(gateways["VpnGateways"]) == 1
    assert gateways["VpnGateways"][0]["VpnGatewayId"] == gateway_id
    assert {"State": "attached", "VpcId": vpc_id} in gateways["VpnGateways"][0][
        "VpcAttachments"
    ]


@mock_aws
def test_describe_vpn_connections_state_filter_attached():
    """describe_vpn_gateways attachment.state filter - match attached"""

    ec2 = boto3.client("ec2", region_name="us-east-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    vpc_id = vpc["Vpc"]["VpcId"]
    gateway = ec2.create_vpn_gateway(AvailabilityZone="us-east-1a", Type="ipsec.1")
    gateway_id = gateway["VpnGateway"]["VpnGatewayId"]

    ec2.attach_vpn_gateway(VpcId=vpc_id, VpnGatewayId=gateway_id)

    all_gateways = retrieve_all(
        ec2, [{"Name": "attachment.state", "Values": ["attached"]}]
    )

    assert gateway_id in [gw["VpnGatewayId"] for gw in all_gateways]
    my_gateway = [gw for gw in all_gateways if gw["VpnGatewayId"] == gateway_id][0]
    assert {"State": "attached", "VpcId": vpc_id} in my_gateway["VpcAttachments"]


@mock_aws
def test_virtual_private_gateways_boto3():
    client = boto3.client("ec2", region_name="us-west-1")

    vpn_gateway = client.create_vpn_gateway(
        Type="ipsec.1", AvailabilityZone="us-east-1a"
    )["VpnGateway"]

    assert vpn_gateway["VpnGatewayId"].startswith("vgw-")
    assert vpn_gateway["Type"] == "ipsec.1"
    assert vpn_gateway["State"] == "available"
    assert vpn_gateway["AvailabilityZone"] == "us-east-1a"


@mock_aws
def test_describe_vpn_gateway_boto3():
    client = boto3.client("ec2", region_name="us-west-1")
    vpn_gateway = client.create_vpn_gateway(
        Type="ipsec.1", AvailabilityZone="us-east-1a"
    )["VpnGateway"]

    vgws = client.describe_vpn_gateways(VpnGatewayIds=[vpn_gateway["VpnGatewayId"]])[
        "VpnGateways"
    ]
    assert len(vgws) == 1

    gateway = vgws[0]
    assert gateway["VpnGatewayId"].startswith("vgw-")
    assert gateway["VpnGatewayId"] == vpn_gateway["VpnGatewayId"]
    # TODO: fixme. This currently returns the ID
    # assert gateway["Type"] == "ipsec.1"
    assert gateway["State"] == "available"
    assert gateway["AvailabilityZone"] == "us-east-1a"


@mock_aws
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

    assert len(gateways["VpnGateways"]) == 0


@mock_aws
def test_describe_vpn_connections_id_filter_match():
    """describe_vpn_gateways vpn-gateway-id filter - match correct id"""

    ec2 = boto3.client("ec2", region_name="us-east-1")

    gateway = ec2.create_vpn_gateway(AvailabilityZone="us-east-1a", Type="ipsec.1")
    gateway_id = gateway["VpnGateway"]["VpnGatewayId"]

    gateways = ec2.describe_vpn_gateways(
        Filters=[{"Name": "vpn-gateway-id", "Values": [gateway_id]}]
    )

    assert len(gateways["VpnGateways"]) == 1
    assert gateways["VpnGateways"][0]["VpnGatewayId"] == gateway_id


@mock_aws
def test_describe_vpn_connections_id_filter_miss():
    """describe_vpn_gateways vpn-gateway-id filter - don't match"""

    ec2 = boto3.client("ec2", region_name="us-east-1")

    ec2.create_vpn_gateway(AvailabilityZone="us-east-1a", Type="ipsec.1")

    gateways = ec2.describe_vpn_gateways(
        Filters=[{"Name": "vpn-gateway-id", "Values": ["unknown_gateway_id"]}]
    )

    assert len(gateways["VpnGateways"]) == 0


@mock_aws
def test_describe_vpn_connections_type_filter_match():
    """describe_vpn_gateways type filter - match"""

    ec2 = boto3.client("ec2", region_name="us-east-1")

    gateway = ec2.create_vpn_gateway(AvailabilityZone="us-east-1a", Type="ipsec.1")
    gateway_id = gateway["VpnGateway"]["VpnGatewayId"]

    my_gateways = retrieve_all(ec2, [{"Name": "type", "Values": ["ipsec.1"]}])

    assert gateway_id in [gw["VpnGatewayId"] for gw in my_gateways]


@mock_aws
def test_describe_vpn_connections_type_filter_miss():
    """describe_vpn_gateways type filter - don't match"""

    ec2 = boto3.client("ec2", region_name="us-east-1")

    ec2.create_vpn_gateway(AvailabilityZone="us-east-1a", Type="ipsec.1")

    gateways = ec2.describe_vpn_gateways(
        Filters=[{"Name": "type", "Values": ["unknown_type"]}]
    )

    assert len(gateways["VpnGateways"]) == 0


@mock_aws
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
    assert attachments == [{"State": "attached", "VpcId": vpc.id}]


@mock_aws
def test_delete_vpn_gateway_boto3():
    client = boto3.client("ec2", region_name="us-west-1")
    vpn_gateway = client.create_vpn_gateway(
        Type="ipsec.1", AvailabilityZone="us-east-1a"
    )["VpnGateway"]
    vpng_id = vpn_gateway["VpnGatewayId"]

    client.delete_vpn_gateway(VpnGatewayId=vpng_id)
    gateways = client.describe_vpn_gateways(VpnGatewayIds=[vpng_id])["VpnGateways"]
    assert len(gateways) == 1
    assert gateways[0]["State"] == "deleted"


@mock_aws
def test_vpn_gateway_tagging_boto3():
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
    assert ours["Key"] == "a key"
    assert ours["Value"] == "some value"

    vpn_gateway = client.describe_vpn_gateways()["VpnGateways"][0]
    # TODO: Fixme: Tags is currently empty
    # assert vpn_gateway["Tags"] == [{'Key': 'a key', 'Value': 'some value'}]


@mock_aws
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
    assert attachments == [{"State": "attached", "VpcId": vpc.id}]

    client.detach_vpn_gateway(VpnGatewayId=vpng_id, VpcId=vpc.id)

    gateway = client.describe_vpn_gateways(VpnGatewayIds=[vpng_id])["VpnGateways"][0]
    attachments = gateway["VpcAttachments"]
    assert attachments == [{"State": "detached", "VpcId": vpc.id}]


def retrieve_all(client, filters=[]):  # pylint: disable=W0102
    resp = client.describe_vpn_gateways(Filters=filters)
    all_gateways = resp["VpnGateways"]
    token = resp.get("NextToken")
    while token:
        resp = client.describe_vpn_gateways(Filters=filters)
        all_gateways.extend(resp["VpnGateways"])
        token = resp.get("NextToken")
    return all_gateways
