from unittest import SkipTest

import boto3

from moto import mock_aws, settings


@mock_aws
def test_describe_nat_gateways():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("ServerMode is not guaranteed to have no resources")
    conn = boto3.client("ec2", "us-east-1")

    response = conn.describe_nat_gateways()

    assert len(response["NatGateways"]) == 0


@mock_aws
def test_create_nat_gateway():
    conn = boto3.client("ec2", "us-east-1")
    vpc = conn.create_vpc(CidrBlock="10.0.0.0/16")
    vpc_id = vpc["Vpc"]["VpcId"]
    subnet = conn.create_subnet(
        VpcId=vpc_id, CidrBlock="10.0.1.0/27", AvailabilityZone="us-east-1a"
    )
    allocation_id = conn.allocate_address(Domain="vpc")["AllocationId"]
    subnet_id = subnet["Subnet"]["SubnetId"]

    response = conn.create_nat_gateway(SubnetId=subnet_id, AllocationId=allocation_id)

    assert response["NatGateway"]["VpcId"] == vpc_id
    assert response["NatGateway"]["SubnetId"] == subnet_id
    assert response["NatGateway"]["State"] == "available"


@mock_aws
def test_describe_nat_gateway_tags():
    conn = boto3.client("ec2", "us-east-1")
    vpc = conn.create_vpc(CidrBlock="10.0.0.0/16")
    vpc_id = vpc["Vpc"]["VpcId"]
    subnet = conn.create_subnet(
        VpcId=vpc_id, CidrBlock="10.0.1.0/27", AvailabilityZone="us-east-1a"
    )
    allocation_id = conn.allocate_address(Domain="vpc")["AllocationId"]
    subnet_id = subnet["Subnet"]["SubnetId"]

    gateway = conn.create_nat_gateway(
        SubnetId=subnet_id,
        AllocationId=allocation_id,
        TagSpecifications=[
            {
                "ResourceType": "nat-gateway",
                "Tags": [
                    {"Key": "name", "Value": "some-nat-gateway"},
                    {"Key": "name1", "Value": "some-nat-gateway-1"},
                ],
            }
        ],
    )["NatGateway"]

    describe_all = retrieve_all_gateways(conn)
    assert vpc_id in [gw["VpcId"] for gw in describe_all]
    describe_gateway = [gw for gw in describe_all if gw["VpcId"] == vpc_id]

    assert describe_gateway[0]["NatGatewayId"] == gateway["NatGatewayId"]
    assert describe_gateway[0]["VpcId"] == vpc_id
    assert describe_gateway[0]["Tags"] == [
        {"Key": "name", "Value": "some-nat-gateway"},
        {"Key": "name1", "Value": "some-nat-gateway-1"},
    ]


@mock_aws
def test_delete_nat_gateway():
    conn = boto3.client("ec2", "us-east-1")
    vpc = conn.create_vpc(CidrBlock="10.0.0.0/16")
    vpc_id = vpc["Vpc"]["VpcId"]
    subnet = conn.create_subnet(
        VpcId=vpc_id, CidrBlock="10.0.1.0/27", AvailabilityZone="us-east-1a"
    )
    allocation_id = conn.allocate_address(Domain="vpc")["AllocationId"]
    subnet_id = subnet["Subnet"]["SubnetId"]

    nat_gateway = conn.create_nat_gateway(
        SubnetId=subnet_id, AllocationId=allocation_id
    )
    nat_gateway_id = nat_gateway["NatGateway"]["NatGatewayId"]
    response = conn.delete_nat_gateway(NatGatewayId=nat_gateway_id)

    # this is hard to match against, so remove it
    response["ResponseMetadata"].pop("HTTPHeaders", None)
    response["ResponseMetadata"].pop("RetryAttempts", None)
    assert response == {
        "NatGatewayId": nat_gateway_id,
        "ResponseMetadata": {
            "HTTPStatusCode": 200,
            "RequestId": "741fc8ab-6ebe-452b-b92b-example",
        },
    }


@mock_aws
def test_create_and_describe_nat_gateway():
    conn = boto3.client("ec2", "us-east-1")
    vpc = conn.create_vpc(CidrBlock="10.0.0.0/16")
    vpc_id = vpc["Vpc"]["VpcId"]
    subnet = conn.create_subnet(
        VpcId=vpc_id, CidrBlock="10.0.1.0/27", AvailabilityZone="us-east-1a"
    )
    allocation_id = conn.allocate_address(Domain="vpc")["AllocationId"]
    subnet_id = subnet["Subnet"]["SubnetId"]

    create_response = conn.create_nat_gateway(
        SubnetId=subnet_id, AllocationId=allocation_id
    )
    nat_gateway_id = create_response["NatGateway"]["NatGatewayId"]
    net_interface_id = create_response["NatGateway"]["NatGatewayAddresses"][0][
        "NetworkInterfaceId"
    ]

    public_ip = conn.describe_addresses(AllocationIds=[allocation_id])["Addresses"][0][
        "PublicIp"
    ]

    describe = conn.describe_nat_gateways(NatGatewayIds=[nat_gateway_id])["NatGateways"]

    assert len(describe) == 1
    assert describe[0]["NatGatewayId"] == nat_gateway_id
    assert describe[0]["State"] == "available"
    assert describe[0]["SubnetId"] == subnet_id
    assert describe[0]["VpcId"] == vpc_id
    assert describe[0]["NatGatewayAddresses"][0]["AllocationId"] == allocation_id
    assert (
        describe[0]["NatGatewayAddresses"][0]["NetworkInterfaceId"] == net_interface_id
    )
    assert describe[0]["NatGatewayAddresses"][0]["PrivateIp"].startswith("10.")
    assert describe[0]["NatGatewayAddresses"][0]["PublicIp"] == public_ip


@mock_aws
def test_describe_nat_gateway_filter_by_net_gateway_id_and_state():
    conn = boto3.client("ec2", "us-east-1")
    vpc = conn.create_vpc(CidrBlock="10.0.0.0/16")
    vpc_id = vpc["Vpc"]["VpcId"]
    subnet = conn.create_subnet(
        VpcId=vpc_id, CidrBlock="10.0.1.0/27", AvailabilityZone="us-east-1a"
    )
    allocation_id = conn.allocate_address(Domain="vpc")["AllocationId"]
    subnet_id = subnet["Subnet"]["SubnetId"]

    create_response = conn.create_nat_gateway(
        SubnetId=subnet_id, AllocationId=allocation_id
    )
    nat_gateway_id = create_response["NatGateway"]["NatGatewayId"]

    describe_response = conn.describe_nat_gateways(
        Filters=[
            {"Name": "nat-gateway-id", "Values": ["non-existent-id"]},
            {"Name": "state", "Values": ["available"]},
        ]
    )
    assert len(describe_response["NatGateways"]) == 0

    describe_response = conn.describe_nat_gateways(
        Filters=[
            {"Name": "nat-gateway-id", "Values": [nat_gateway_id]},
            {"Name": "state", "Values": ["available"]},
        ]
    )

    assert len(describe_response["NatGateways"]) == 1
    assert describe_response["NatGateways"][0]["NatGatewayId"] == nat_gateway_id
    assert describe_response["NatGateways"][0]["State"] == "available"
    assert describe_response["NatGateways"][0]["SubnetId"] == subnet_id
    assert describe_response["NatGateways"][0]["VpcId"] == vpc_id
    assert (
        describe_response["NatGateways"][0]["NatGatewayAddresses"][0]["AllocationId"]
        == allocation_id
    )


@mock_aws
def test_describe_nat_gateway_filter_by_subnet_id():
    conn = boto3.client("ec2", "us-east-1")
    vpc = conn.create_vpc(CidrBlock="10.0.0.0/16")
    vpc_id = vpc["Vpc"]["VpcId"]
    subnet_1 = conn.create_subnet(
        VpcId=vpc_id, CidrBlock="10.0.1.0/27", AvailabilityZone="us-east-1a"
    )
    subnet_2 = conn.create_subnet(
        VpcId=vpc_id, CidrBlock="10.0.2.0/27", AvailabilityZone="us-east-1a"
    )
    allocation_id_1 = conn.allocate_address(Domain="vpc")["AllocationId"]
    allocation_id_2 = conn.allocate_address(Domain="vpc")["AllocationId"]
    subnet_id_1 = subnet_1["Subnet"]["SubnetId"]
    subnet_id_2 = subnet_2["Subnet"]["SubnetId"]

    create_response_1 = conn.create_nat_gateway(
        SubnetId=subnet_id_1, AllocationId=allocation_id_1
    )
    # create_response_2 =
    conn.create_nat_gateway(SubnetId=subnet_id_2, AllocationId=allocation_id_2)
    nat_gateway_id_1 = create_response_1["NatGateway"]["NatGatewayId"]
    # nat_gateway_id_2 = create_response_2["NatGateway"]["NatGatewayId"]

    all_gws = retrieve_all_gateways(conn)
    all_gw_ids = [gw["NatGatewayId"] for gw in all_gws]
    assert nat_gateway_id_1 in all_gw_ids

    describe_response = conn.describe_nat_gateways(
        Filters=[{"Name": "subnet-id", "Values": [subnet_id_1]}]
    )
    assert len(describe_response["NatGateways"]) == 1
    assert describe_response["NatGateways"][0]["NatGatewayId"] == nat_gateway_id_1
    assert describe_response["NatGateways"][0]["State"] == "available"
    assert describe_response["NatGateways"][0]["SubnetId"] == subnet_id_1
    assert describe_response["NatGateways"][0]["VpcId"] == vpc_id
    assert (
        describe_response["NatGateways"][0]["NatGatewayAddresses"][0]["AllocationId"]
        == allocation_id_1
    )


@mock_aws
def test_describe_nat_gateway_filter_vpc_id():
    conn = boto3.client("ec2", "us-east-1")
    vpc_1 = conn.create_vpc(CidrBlock="10.0.0.0/16")
    vpc_id_1 = vpc_1["Vpc"]["VpcId"]
    vpc_2 = conn.create_vpc(CidrBlock="10.1.0.0/16")
    vpc_id_2 = vpc_2["Vpc"]["VpcId"]
    subnet_1 = conn.create_subnet(
        VpcId=vpc_id_1, CidrBlock="10.0.1.0/27", AvailabilityZone="us-east-1a"
    )
    subnet_2 = conn.create_subnet(
        VpcId=vpc_id_2, CidrBlock="10.1.1.0/27", AvailabilityZone="us-east-1a"
    )
    allocation_id_1 = conn.allocate_address(Domain="vpc")["AllocationId"]
    allocation_id_2 = conn.allocate_address(Domain="vpc")["AllocationId"]
    subnet_id_1 = subnet_1["Subnet"]["SubnetId"]
    subnet_id_2 = subnet_2["Subnet"]["SubnetId"]

    create_response_1 = conn.create_nat_gateway(
        SubnetId=subnet_id_1, AllocationId=allocation_id_1
    )
    conn.create_nat_gateway(SubnetId=subnet_id_2, AllocationId=allocation_id_2)
    nat_gateway_id_1 = create_response_1["NatGateway"]["NatGatewayId"]

    describe_response = conn.describe_nat_gateways(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id_1]}]
    )
    assert len(describe_response["NatGateways"]) == 1
    assert describe_response["NatGateways"][0]["NatGatewayId"] == nat_gateway_id_1
    assert describe_response["NatGateways"][0]["State"] == "available"
    assert describe_response["NatGateways"][0]["SubnetId"] == subnet_id_1
    assert describe_response["NatGateways"][0]["VpcId"] == vpc_id_1
    assert (
        describe_response["NatGateways"][0]["NatGatewayAddresses"][0]["AllocationId"]
        == allocation_id_1
    )


def retrieve_all_gateways(client, filters=[]):  # pylint: disable=W0102
    resp = client.describe_nat_gateways(Filters=filters)
    all_gws = resp["NatGateways"]
    token = resp.get("NextToken")
    while token:
        resp = client.describe_nat_gateways(Filters=filters, NextToken=token)
        all_gws.extend(resp["NatGateways"])
        token = resp.get("NextToken")
    return all_gws
