from __future__ import unicode_literals
import boto3

import sure  # noqa
from moto import mock_ec2


@mock_ec2
def test_describe_nat_gateways():
    conn = boto3.client("ec2", "us-east-1")

    response = conn.describe_nat_gateways()

    response["NatGateways"].should.have.length_of(0)


@mock_ec2
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

    response["NatGateway"]["VpcId"].should.equal(vpc_id)
    response["NatGateway"]["SubnetId"].should.equal(subnet_id)
    response["NatGateway"]["State"].should.equal("available")


@mock_ec2
def test_describe_nat_gateway_tags():
    conn = boto3.client("ec2", "us-east-1")
    vpc = conn.create_vpc(CidrBlock="10.0.0.0/16")
    vpc_id = vpc["Vpc"]["VpcId"]
    subnet = conn.create_subnet(
        VpcId=vpc_id, CidrBlock="10.0.1.0/27", AvailabilityZone="us-east-1a"
    )
    allocation_id = conn.allocate_address(Domain="vpc")["AllocationId"]
    subnet_id = subnet["Subnet"]["SubnetId"]

    conn.create_nat_gateway(
        SubnetId=subnet_id,
        AllocationId=allocation_id,
        TagSpecifications=[
            {
                "ResourceType": "nat-gateway",
                "Tags": [
                    {"Key": "name", "Value": "some-nat-gateway"},
                    {"Key": "name", "Value": "some-nat-gateway-1"},
                ],
            }
        ],
    )

    describe_response = conn.describe_nat_gateways()

    assert describe_response["NatGateways"][0]["VpcId"] == vpc_id
    assert describe_response["NatGateways"][0]["Tags"] == [
        {"Key": "name", "Value": "some-nat-gateway"},
        {"Key": "name", "Value": "some-nat-gateway-1"},
    ]


@mock_ec2
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
    response.should.equal(
        {
            "NatGatewayId": nat_gateway_id,
            "ResponseMetadata": {
                "HTTPStatusCode": 200,
                "RequestId": "741fc8ab-6ebe-452b-b92b-example",
            },
        }
    )


@mock_ec2
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
    describe_response = conn.describe_nat_gateways()

    enis = conn.describe_network_interfaces()["NetworkInterfaces"]
    eni_id = enis[0]["NetworkInterfaceId"]
    public_ip = conn.describe_addresses(AllocationIds=[allocation_id])["Addresses"][0][
        "PublicIp"
    ]

    describe_response["NatGateways"].should.have.length_of(1)
    describe_response["NatGateways"][0]["NatGatewayId"].should.equal(nat_gateway_id)
    describe_response["NatGateways"][0]["State"].should.equal("available")
    describe_response["NatGateways"][0]["SubnetId"].should.equal(subnet_id)
    describe_response["NatGateways"][0]["VpcId"].should.equal(vpc_id)
    describe_response["NatGateways"][0]["NatGatewayAddresses"][0][
        "AllocationId"
    ].should.equal(allocation_id)
    describe_response["NatGateways"][0]["NatGatewayAddresses"][0][
        "NetworkInterfaceId"
    ].should.equal(eni_id)
    assert describe_response["NatGateways"][0]["NatGatewayAddresses"][0][
        "PrivateIp"
    ].startswith("10.")
    describe_response["NatGateways"][0]["NatGatewayAddresses"][0][
        "PublicIp"
    ].should.equal(public_ip)


@mock_ec2
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
    describe_response["NatGateways"].should.have.length_of(0)

    describe_response = conn.describe_nat_gateways(
        Filters=[
            {"Name": "nat-gateway-id", "Values": [nat_gateway_id]},
            {"Name": "state", "Values": ["available"]},
        ]
    )

    describe_response["NatGateways"].should.have.length_of(1)
    describe_response["NatGateways"][0]["NatGatewayId"].should.equal(nat_gateway_id)
    describe_response["NatGateways"][0]["State"].should.equal("available")
    describe_response["NatGateways"][0]["SubnetId"].should.equal(subnet_id)
    describe_response["NatGateways"][0]["VpcId"].should.equal(vpc_id)
    describe_response["NatGateways"][0]["NatGatewayAddresses"][0][
        "AllocationId"
    ].should.equal(allocation_id)


@mock_ec2
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

    describe_response = conn.describe_nat_gateways()
    describe_response["NatGateways"].should.have.length_of(2)

    describe_response = conn.describe_nat_gateways(
        Filters=[{"Name": "subnet-id", "Values": [subnet_id_1]}]
    )
    describe_response["NatGateways"].should.have.length_of(1)
    describe_response["NatGateways"][0]["NatGatewayId"].should.equal(nat_gateway_id_1)
    describe_response["NatGateways"][0]["State"].should.equal("available")
    describe_response["NatGateways"][0]["SubnetId"].should.equal(subnet_id_1)
    describe_response["NatGateways"][0]["VpcId"].should.equal(vpc_id)
    describe_response["NatGateways"][0]["NatGatewayAddresses"][0][
        "AllocationId"
    ].should.equal(allocation_id_1)


@mock_ec2
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

    describe_response = conn.describe_nat_gateways()
    describe_response["NatGateways"].should.have.length_of(2)

    describe_response = conn.describe_nat_gateways(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id_1]}]
    )
    describe_response["NatGateways"].should.have.length_of(1)
    describe_response["NatGateways"][0]["NatGatewayId"].should.equal(nat_gateway_id_1)
    describe_response["NatGateways"][0]["State"].should.equal("available")
    describe_response["NatGateways"][0]["SubnetId"].should.equal(subnet_id_1)
    describe_response["NatGateways"][0]["VpcId"].should.equal(vpc_id_1)
    describe_response["NatGateways"][0]["NatGatewayAddresses"][0][
        "AllocationId"
    ].should.equal(allocation_id_1)
