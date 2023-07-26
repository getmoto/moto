import boto3
import pytest

from botocore.exceptions import ClientError
from moto import mock_ec2, mock_elbv2
from moto.moto_api._internal import mock_random

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_ec2
def test_create_vpc_endpoint_service_configuration_without_params():
    client = boto3.client("ec2", region_name="us-west-2")

    with pytest.raises(ClientError) as exc:
        client.create_vpc_endpoint_service_configuration()
    err = exc.value.response["Error"]

    assert err["Code"] == "InvalidParameter"
    assert (
        err["Message"]
        == "exactly one of network_load_balancer_arn or gateway_load_balancer_arn is a required member"
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
    assert "ServiceConfiguration" in resp
    config = resp["ServiceConfiguration"]

    assert config["ServiceType"] == [{"ServiceType": "Interface"}]
    assert config["ServiceId"].startswith("vpce-svc-")
    assert (
        config["ServiceName"] == f"com.amazonaws.vpce.eu-west-3.{config['ServiceId']}"
    )
    assert config["ServiceState"] == "Available"
    assert config["AvailabilityZones"] == ["eu-west-3b"]
    assert config["AcceptanceRequired"] is True
    assert config["ManagesVpcEndpoints"] is False
    assert config["NetworkLoadBalancerArns"] == [lb_arn]
    assert config["BaseEndpointDnsNames"] == [
        f"{config['ServiceId']}.eu-west-3.vpce.amazonaws.com"
    ]
    assert config["PrivateDnsNameConfiguration"] == {}

    assert "GatewayLoadBalancerArns" not in config


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
    assert "ServiceConfiguration" in resp
    config = resp["ServiceConfiguration"]

    assert config["ServiceType"] == [{"ServiceType": "Gateway"}]
    assert config["ServiceId"].startswith("vpce-svc-")
    assert (
        config["ServiceName"] == f"com.amazonaws.vpce.us-east-2.{config['ServiceId']}"
    )
    assert config["ServiceState"] == "Available"
    assert config["AvailabilityZones"] == ["us-east-1c"]
    assert config["AcceptanceRequired"] is True
    assert config["ManagesVpcEndpoints"] is False
    assert config["GatewayLoadBalancerArns"] == [lb_arn]
    assert config["BaseEndpointDnsNames"] == [
        f"{config['ServiceId']}.us-east-2.vpce.amazonaws.com"
    ]
    assert config["PrivateDnsNameConfiguration"] == {}

    assert "NetworkLoadBalancerArns" not in config


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
    assert "ServiceConfiguration" in resp
    config = resp["ServiceConfiguration"]

    assert config["AcceptanceRequired"] is False
    assert config["PrivateDnsName"] == "example.com"
    assert config["PrivateDnsNameConfiguration"] == {
        "Name": "n",
        "State": "verified",
        "Type": "TXT",
        "Value": "val",
    }


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
    assert "ServiceConfigurations" in resp
    service_ids = [s["ServiceId"] for s in resp["ServiceConfigurations"]]
    assert config1 in service_ids
    assert config2 in service_ids

    resp = client.describe_vpc_endpoint_service_configurations(ServiceIds=[config2])

    assert len(resp["ServiceConfigurations"]) == 1
    result = resp["ServiceConfigurations"][0]

    assert result["ServiceId"] == config2
    assert "ServiceName" in result
    assert "ServiceState" in result
    assert result["GatewayLoadBalancerArns"] == [lb_arn]


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

    assert len(resp["ServiceConfigurations"]) == 1
    result = resp["ServiceConfigurations"][0]
    assert len(result["Tags"]) == len(tags)
    for tag in tags:
        assert tag in result["Tags"]


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

    assert len(resp["ServiceConfigurations"]) == 1
    result = resp["ServiceConfigurations"][0]
    assert len(result["Tags"]) == len(tags)
    for tag in tags:
        assert tag in result["Tags"]


@mock_ec2
def test_describe_vpc_endpoint_service_configurations_unknown():
    client = boto3.client("ec2", region_name="eu-west-3")

    with pytest.raises(ClientError) as exc:
        # Will always fail if at least one ServiceId is unknown
        client.describe_vpc_endpoint_service_configurations(
            ServiceIds=["vpce-svc-unknown"]
        )
    err = exc.value.response["Error"]

    assert err["Code"] == "InvalidVpcEndpointServiceId.NotFound"
    assert (
        err["Message"] == "The VpcEndpointService Id 'vpce-svc-unknown' does not exist"
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
    assert resp["Unsuccessful"] == []


@mock_ec2
def test_delete_vpc_endpoint_service_configurations_already_deleted():
    client = boto3.client("ec2", region_name="eu-west-3")

    resp = client.delete_vpc_endpoint_service_configurations(
        ServiceIds=["vpce-svc-03cf101d15c3bff53"]
    )
    assert len(resp["Unsuccessful"]) == 1

    u = resp["Unsuccessful"][0]
    assert u["ResourceId"] == "vpce-svc-03cf101d15c3bff53"

    assert u["Error"]["Code"] == "InvalidVpcEndpointService.NotFound"
    assert (
        u["Error"]["Message"]
        == "The VpcEndpointService Id 'vpce-svc-03cf101d15c3bff53' does not exist"
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
    assert resp["AllowedPrincipals"] == []


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
    assert len(resp["AllowedPrincipals"]) == 2
    assert {"Principal": "prin1"} in resp["AllowedPrincipals"]
    assert {"Principal": "cipal2"} in resp["AllowedPrincipals"]

    client.modify_vpc_endpoint_service_permissions(
        ServiceId=service_id, RemoveAllowedPrincipals=["prin1"]
    )

    resp = client.describe_vpc_endpoint_service_permissions(ServiceId=service_id)
    assert len(resp["AllowedPrincipals"]) == 1
    assert {"Principal": "cipal2"} in resp["AllowedPrincipals"]


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

    assert config["AcceptanceRequired"] is False
    assert config["PrivateDnsName"] == "dnsname"


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
    assert config["GatewayLoadBalancerArns"] == [lb_arn, lb_arn2]
    assert config["NetworkLoadBalancerArns"] == [lb_arn3]

    client.modify_vpc_endpoint_service_configuration(
        ServiceId=service_id,
        RemoveNetworkLoadBalancerArns=[lb_arn3],
        RemoveGatewayLoadBalancerArns=[lb_arn],
    )

    config = client.describe_vpc_endpoint_service_configurations(
        ServiceIds=[service_id]
    )["ServiceConfigurations"][0]
    assert config["GatewayLoadBalancerArns"] == [lb_arn2]
    assert "NetworkLoadBalancerArns" not in config


def create_load_balancer(region_name, zone, lb_type):
    ec2 = boto3.resource("ec2", region_name=region_name)
    elbv2 = boto3.client("elbv2", region_name=region_name)

    vpc = ec2.create_vpc(CidrBlock="172.28.7.0/24", InstanceTenancy="default")
    subnet = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="172.28.7.192/26", AvailabilityZone=zone
    )
    lb_name = f"lb_vpce-{mock_random.get_random_hex(length=10)}"
    response = elbv2.create_load_balancer(
        Name=lb_name, Subnets=[subnet.id], Scheme="internal", Type=lb_type
    )
    return response["LoadBalancers"][0]["LoadBalancerArn"]
