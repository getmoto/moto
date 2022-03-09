import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import

from botocore.exceptions import ClientError
from moto import mock_ec2, mock_elbv2
from moto.core.utils import get_random_hex

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_ec2
def test_create_vpc_endpoint_service_configuration_without_params():
    client = boto3.client("ec2", region_name="us-west-2")

    with pytest.raises(ClientError) as exc:
        client.create_vpc_endpoint_service_configuration()
    err = exc.value.response["Error"]

    err["Code"].should.equal("InvalidParameter")
    err["Message"].should.equal(
        "exactly one of network_load_balancer_arn or gateway_load_balancer_arn is a required member"
    )


@mock_ec2
@mock_elbv2
def test_create_vpc_endpoint_service_configuration_with_network_load_balancer():
    region_name = "eu-west-3"
    client = boto3.client("ec2", region_name=region_name)

    lb_arn = create_load_balancer(
        region_name=region_name, lb_type="network", zone="eu-west-3b"
    )

    resp = client.create_vpc_endpoint_service_configuration(
        NetworkLoadBalancerArns=[lb_arn]
    )
    resp.should.have.key("ServiceConfiguration")
    config = resp["ServiceConfiguration"]

    config.should.have.key("ServiceType").equals([{"ServiceType": "Interface"}])
    config.should.have.key("ServiceId").match("^vpce-svc-")
    config.should.have.key("ServiceName").equals(
        f"com.amazonaws.vpce.eu-west-3.{config['ServiceId']}"
    )
    config.should.have.key("ServiceState").equals("Available")
    config.should.have.key("AvailabilityZones").equals(["eu-west-3b"])
    config.should.have.key("AcceptanceRequired").equals(True)
    config.should.have.key("ManagesVpcEndpoints").equals(False)
    config.should.have.key("NetworkLoadBalancerArns").equals([lb_arn])
    config.should.have.key("BaseEndpointDnsNames").equals(
        [f"{config['ServiceId']}.eu-west-3.vpce.amazonaws.com"]
    )
    config.should.have.key("PrivateDnsNameConfiguration").equals({})

    config.shouldnt.have.key("GatewayLoadBalancerArns")


@mock_ec2
@mock_elbv2
def test_create_vpc_endpoint_service_configuration_with_gateway_load_balancer():
    region = "us-east-2"
    client = boto3.client("ec2", region_name=region)

    lb_arn = create_load_balancer(
        region_name=region, lb_type="gateway", zone="us-east-1c"
    )

    resp = client.create_vpc_endpoint_service_configuration(
        GatewayLoadBalancerArns=[lb_arn]
    )
    resp.should.have.key("ServiceConfiguration")
    config = resp["ServiceConfiguration"]

    config.should.have.key("ServiceType").equals([{"ServiceType": "Gateway"}])
    config.should.have.key("ServiceId").match("^vpce-svc-")
    config.should.have.key("ServiceName").equals(
        f"com.amazonaws.vpce.us-east-2.{config['ServiceId']}"
    )
    config.should.have.key("ServiceState").equals("Available")
    config.should.have.key("AvailabilityZones").equals(["us-east-1c"])
    config.should.have.key("AcceptanceRequired").equals(True)
    config.should.have.key("ManagesVpcEndpoints").equals(False)
    config.should.have.key("GatewayLoadBalancerArns").equals([lb_arn])
    config.should.have.key("BaseEndpointDnsNames").equals(
        [f"{config['ServiceId']}.us-east-2.vpce.amazonaws.com"]
    )
    config.should.have.key("PrivateDnsNameConfiguration").equals({})

    config.shouldnt.have.key("NetworkLoadBalancerArns")


@mock_ec2
@mock_elbv2
def test_create_vpc_endpoint_service_configuration_with_options():
    client = boto3.client("ec2", region_name="us-east-2")

    lb_arn = create_load_balancer(
        region_name="us-east-2", lb_type="gateway", zone="us-east-1c"
    )

    resp = client.create_vpc_endpoint_service_configuration(
        GatewayLoadBalancerArns=[lb_arn],
        AcceptanceRequired=False,
        PrivateDnsName="example.com",
    )
    resp.should.have.key("ServiceConfiguration")
    config = resp["ServiceConfiguration"]

    config.should.have.key("AcceptanceRequired").equals(False)
    config.should.have.key("PrivateDnsName").equals("example.com")
    config.should.have.key("PrivateDnsNameConfiguration").equals(
        {"Name": "n", "State": "verified", "Type": "TXT", "Value": "val"}
    )


@mock_ec2
@mock_elbv2
def test_describe_vpc_endpoint_service_configurations():
    region = "us-east-2"
    client = boto3.client("ec2", region_name=region)

    lb_arn = create_load_balancer(
        region_name=region, lb_type="gateway", zone="us-east-1c"
    )

    config1 = client.create_vpc_endpoint_service_configuration(
        GatewayLoadBalancerArns=[lb_arn]
    )["ServiceConfiguration"]["ServiceId"]
    config2 = client.create_vpc_endpoint_service_configuration(
        GatewayLoadBalancerArns=[lb_arn]
    )["ServiceConfiguration"]["ServiceId"]

    resp = client.describe_vpc_endpoint_service_configurations()
    resp.should.have.key("ServiceConfigurations")
    service_ids = [s["ServiceId"] for s in resp["ServiceConfigurations"]]
    service_ids.should.contain(config1)
    service_ids.should.contain(config2)

    resp = client.describe_vpc_endpoint_service_configurations(ServiceIds=[config2])

    resp.should.have.key("ServiceConfigurations").length_of(1)
    result = resp["ServiceConfigurations"][0]

    result.should.have.key("ServiceId").equals(config2)
    result.should.have.key("ServiceName")
    result.should.have.key("ServiceState")
    result.should.have.key("GatewayLoadBalancerArns").equals([lb_arn])


@mock_ec2
@mock_elbv2
@pytest.mark.parametrize(
    "tags",
    [
        [{"Key": "k1", "Value": "v1"}],
        [{"Key": "k1", "Value": "v1"}, {"Key": "k2", "Value": "v2"}],
    ],
)
def test_describe_vpc_endpoint_service_configurations_with_tags(tags):
    region = "us-east-2"
    client = boto3.client("ec2", region_name=region)

    lb_arn = create_load_balancer(
        region_name=region, lb_type="gateway", zone="us-east-1c"
    )

    service_id = client.create_vpc_endpoint_service_configuration(
        GatewayLoadBalancerArns=[lb_arn],
        TagSpecifications=[{"ResourceType": "vpc-endpoint-service", "Tags": tags}],
    )["ServiceConfiguration"]["ServiceId"]

    resp = client.describe_vpc_endpoint_service_configurations(ServiceIds=[service_id])

    resp.should.have.key("ServiceConfigurations").length_of(1)
    result = resp["ServiceConfigurations"][0]
    result.should.have.key("Tags").length_of(len(tags))
    for tag in tags:
        result["Tags"].should.contain(tag)


@mock_ec2
@mock_elbv2
def test_describe_vpc_endpoint_service_configurations_and_add_tags():
    tags = [{"Key": "k1", "Value": "v1"}]
    region = "us-east-2"
    client = boto3.client("ec2", region_name=region)

    lb_arn = create_load_balancer(
        region_name=region, lb_type="gateway", zone="us-east-1c"
    )

    service_id = client.create_vpc_endpoint_service_configuration(
        GatewayLoadBalancerArns=[lb_arn]
    )["ServiceConfiguration"]["ServiceId"]

    client.create_tags(Resources=[service_id], Tags=tags)

    resp = client.describe_vpc_endpoint_service_configurations(ServiceIds=[service_id])

    resp.should.have.key("ServiceConfigurations").length_of(1)
    result = resp["ServiceConfigurations"][0]
    result.should.have.key("Tags").length_of(len(tags))
    for tag in tags:
        result["Tags"].should.contain(tag)


@mock_ec2
def test_describe_vpc_endpoint_service_configurations_unknown():
    client = boto3.client("ec2", region_name="eu-west-3")

    with pytest.raises(ClientError) as exc:
        # Will always fail if at least one ServiceId is unknown
        client.describe_vpc_endpoint_service_configurations(
            ServiceIds=["vpce-svc-unknown"]
        )
    err = exc.value.response["Error"]

    err["Code"].should.equal("InvalidVpcEndpointServiceId.NotFound")
    err["Message"].should.equal(
        "The VpcEndpointService Id 'vpce-svc-unknown' does not exist"
    )


@mock_ec2
@mock_elbv2
def test_delete_vpc_endpoint_service_configurations():
    region = "us-east-2"
    client = boto3.client("ec2", region_name=region)

    lb_arn = create_load_balancer(
        region_name=region, lb_type="gateway", zone="us-east-1c"
    )

    service_id = client.create_vpc_endpoint_service_configuration(
        GatewayLoadBalancerArns=[lb_arn]
    )["ServiceConfiguration"]["ServiceId"]

    resp = client.delete_vpc_endpoint_service_configurations(ServiceIds=[service_id])
    resp.should.have.key("Unsuccessful").equals([])


@mock_ec2
def test_delete_vpc_endpoint_service_configurations_already_deleted():
    client = boto3.client("ec2", region_name="eu-west-3")

    resp = client.delete_vpc_endpoint_service_configurations(
        ServiceIds=["vpce-svc-03cf101d15c3bff53"]
    )
    resp.should.have.key("Unsuccessful").length_of(1)

    u = resp["Unsuccessful"][0]
    u.should.have.key("ResourceId").equals("vpce-svc-03cf101d15c3bff53")
    u.should.have.key("Error")

    u["Error"].should.have.key("Code").equals("InvalidVpcEndpointService.NotFound")
    u["Error"].should.have.key("Message").equals(
        "The VpcEndpointService Id 'vpce-svc-03cf101d15c3bff53' does not exist"
    )


@mock_ec2
@mock_elbv2
def test_describe_vpc_endpoint_service_permissions():
    region = "us-east-2"
    client = boto3.client("ec2", region_name=region)

    lb_arn = create_load_balancer(
        region_name=region, lb_type="gateway", zone="us-east-1c"
    )

    service_id = client.create_vpc_endpoint_service_configuration(
        GatewayLoadBalancerArns=[lb_arn]
    )["ServiceConfiguration"]["ServiceId"]

    resp = client.describe_vpc_endpoint_service_permissions(ServiceId=service_id)
    resp.should.have.key("AllowedPrincipals").equals([])


@mock_ec2
@mock_elbv2
def test_modify_vpc_endpoint_service_permissions():
    region = "us-east-2"
    client = boto3.client("ec2", region_name=region)

    lb_arn = create_load_balancer(
        region_name=region, lb_type="gateway", zone="us-east-1c"
    )

    service_id = client.create_vpc_endpoint_service_configuration(
        GatewayLoadBalancerArns=[lb_arn]
    )["ServiceConfiguration"]["ServiceId"]

    client.modify_vpc_endpoint_service_permissions(
        ServiceId=service_id, AddAllowedPrincipals=["prin1", "cipal2"]
    )

    resp = client.describe_vpc_endpoint_service_permissions(ServiceId=service_id)
    resp.should.have.key("AllowedPrincipals").length_of(2)
    resp["AllowedPrincipals"].should.contain({"Principal": "prin1"})
    resp["AllowedPrincipals"].should.contain({"Principal": "cipal2"})

    client.modify_vpc_endpoint_service_permissions(
        ServiceId=service_id, RemoveAllowedPrincipals=["prin1"]
    )

    resp = client.describe_vpc_endpoint_service_permissions(ServiceId=service_id)
    resp.should.have.key("AllowedPrincipals").length_of(1)
    resp["AllowedPrincipals"].should.contain({"Principal": "cipal2"})


@mock_ec2
@mock_elbv2
def test_modify_vpc_endpoint_service_configuration():
    region = "us-east-2"
    client = boto3.client("ec2", region_name=region)

    lb_arn = create_load_balancer(
        region_name=region, lb_type="gateway", zone="us-east-1c"
    )

    service_id = client.create_vpc_endpoint_service_configuration(
        GatewayLoadBalancerArns=[lb_arn]
    )["ServiceConfiguration"]["ServiceId"]

    client.modify_vpc_endpoint_service_configuration(
        ServiceId=service_id, PrivateDnsName="dnsname", AcceptanceRequired=False
    )

    config = client.describe_vpc_endpoint_service_configurations(
        ServiceIds=[service_id]
    )["ServiceConfigurations"][0]

    config.should.have.key("AcceptanceRequired").equals(False)
    config.should.have.key("PrivateDnsName").equals("dnsname")


@mock_ec2
@mock_elbv2
def test_modify_vpc_endpoint_service_configuration_with_new_loadbalancers():
    region = "us-east-2"
    client = boto3.client("ec2", region_name=region)

    lb_arn = create_load_balancer(
        region_name=region, lb_type="gateway", zone="us-east-1c"
    )
    lb_arn2 = create_load_balancer(
        region_name=region, lb_type="gateway", zone="us-east-1c"
    )
    lb_arn3 = create_load_balancer(
        region_name=region, lb_type="network", zone="us-east-1c"
    )

    service_id = client.create_vpc_endpoint_service_configuration(
        GatewayLoadBalancerArns=[lb_arn]
    )["ServiceConfiguration"]["ServiceId"]

    client.modify_vpc_endpoint_service_configuration(
        ServiceId=service_id,
        AddNetworkLoadBalancerArns=[lb_arn3],
        AddGatewayLoadBalancerArns=[lb_arn2],
    )

    config = client.describe_vpc_endpoint_service_configurations(
        ServiceIds=[service_id]
    )["ServiceConfigurations"][0]
    config["GatewayLoadBalancerArns"].should.equal([lb_arn, lb_arn2])
    config["NetworkLoadBalancerArns"].should.equal([lb_arn3])

    client.modify_vpc_endpoint_service_configuration(
        ServiceId=service_id,
        RemoveNetworkLoadBalancerArns=[lb_arn3],
        RemoveGatewayLoadBalancerArns=[lb_arn],
    )

    config = client.describe_vpc_endpoint_service_configurations(
        ServiceIds=[service_id]
    )["ServiceConfigurations"][0]
    config["GatewayLoadBalancerArns"].should.equal([lb_arn2])
    config.shouldnt.have.key("NetworkLoadBalancerArns")


def create_load_balancer(region_name, zone, lb_type):
    ec2 = boto3.resource("ec2", region_name=region_name)
    elbv2 = boto3.client("elbv2", region_name=region_name)

    vpc = ec2.create_vpc(CidrBlock="172.28.7.0/24", InstanceTenancy="default")
    subnet = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="172.28.7.192/26", AvailabilityZone=zone
    )
    lb_name = f"lb_vpce-{get_random_hex(length=10)}"
    response = elbv2.create_load_balancer(
        Name=lb_name, Subnets=[subnet.id], Scheme="internal", Type=lb_type
    )
    return response["LoadBalancers"][0]["LoadBalancerArn"]
