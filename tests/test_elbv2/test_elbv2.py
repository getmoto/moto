import copy
import os
import boto3
from botocore.exceptions import ClientError
import pytest

from moto import mock_elbv2, mock_ec2, mock_acm
from moto.elbv2 import elbv2_backends
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from tests import EXAMPLE_AMI_ID


@mock_elbv2
@mock_ec2
def test_create_load_balancer():
    response, _, security_group, subnet1, subnet2, conn = create_load_balancer()

    lb = response["LoadBalancers"][0]
    assert lb["DNSName"] == "my-lb-1.us-east-1.elb.amazonaws.com"
    assert (
        lb["LoadBalancerArn"]
        == f"arn:aws:elasticloadbalancing:us-east-1:{ACCOUNT_ID}:loadbalancer/app/my-lb/50dc6c495c0c9188"
    )
    assert lb["SecurityGroups"] == [security_group.id]
    assert lb["AvailabilityZones"] == [
        {"SubnetId": subnet1.id, "ZoneName": "us-east-1a"},
        {"SubnetId": subnet2.id, "ZoneName": "us-east-1b"},
    ]
    assert lb["CreatedTime"].tzinfo is not None
    assert lb["State"]["Code"] == "provisioning"
    lb_arn = lb["LoadBalancerArn"]

    # Ensure the tags persisted
    tag_desc = conn.describe_tags(ResourceArns=[lb_arn])["TagDescriptions"][0]
    assert tag_desc["ResourceArn"] == lb_arn
    tags = {d["Key"]: d["Value"] for d in tag_desc["Tags"]}
    assert tags == {"key_name": "a_value"}


def create_load_balancer():
    conn = boto3.client("elbv2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    security_group = ec2.create_security_group(
        GroupName="a-security-group", Description="First One"
    )
    vpc = ec2.create_vpc(CidrBlock="172.28.7.0/24", InstanceTenancy="default")
    subnet1 = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="172.28.7.192/26", AvailabilityZone="us-east-1a"
    )
    subnet2 = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="172.28.7.0/26", AvailabilityZone="us-east-1b"
    )

    response = conn.create_load_balancer(
        Name="my-lb",
        Subnets=[subnet1.id, subnet2.id],
        SecurityGroups=[security_group.id],
        Scheme="internal",
        Tags=[{"Key": "key_name", "Value": "a_value"}],
    )
    return response, vpc, security_group, subnet1, subnet2, conn


@mock_elbv2
@mock_ec2
def test_create_elb_using_subnetmapping():
    region = "us-west-1"
    conn = boto3.client("elbv2", region_name=region)
    ec2 = boto3.resource("ec2", region_name=region)

    security_group = ec2.create_security_group(
        GroupName="a-security-group", Description="First One"
    )
    vpc = ec2.create_vpc(CidrBlock="172.28.7.0/24", InstanceTenancy="default")
    subnet1 = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="172.28.7.0/26", AvailabilityZone=region + "a"
    )
    subnet2 = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="172.28.7.192/26", AvailabilityZone=region + "b"
    )

    conn.create_load_balancer(
        Name="my-lb",
        SubnetMappings=[{"SubnetId": subnet1.id}, {"SubnetId": subnet2.id}],
        SecurityGroups=[security_group.id],
        Scheme="internal",
        Tags=[{"Key": "key_name", "Value": "a_value"}],
    )

    lb = conn.describe_load_balancers()["LoadBalancers"][0]
    assert len(lb["AvailabilityZones"]) == 2
    assert {"ZoneName": "us-west-1a", "SubnetId": subnet1.id} in lb["AvailabilityZones"]
    assert {"ZoneName": "us-west-1b", "SubnetId": subnet2.id} in lb["AvailabilityZones"]


@mock_elbv2
@mock_ec2
def test_describe_load_balancers():
    response, _, _, _, _, conn = create_load_balancer()

    response = conn.describe_load_balancers()

    assert len(response["LoadBalancers"]) == 1
    lb = response["LoadBalancers"][0]
    assert lb["LoadBalancerName"] == "my-lb"
    assert lb["State"]["Code"] == "active"

    response = conn.describe_load_balancers(LoadBalancerArns=[lb["LoadBalancerArn"]])
    assert response["LoadBalancers"][0]["LoadBalancerName"] == "my-lb"

    response = conn.describe_load_balancers(Names=["my-lb"])
    assert response["LoadBalancers"][0]["LoadBalancerName"] == "my-lb"

    with pytest.raises(ClientError):
        conn.describe_load_balancers(LoadBalancerArns=["not-a/real/arn"])
    with pytest.raises(ClientError):
        conn.describe_load_balancers(Names=["nope"])


@mock_elbv2
@mock_ec2
def test_describe_listeners():
    conn = boto3.client("elbv2", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        conn.describe_listeners()
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationError"
    assert (
        err["Message"] == "You must specify either listener ARNs or a load balancer ARN"
    )


@mock_elbv2
@mock_ec2
def test_add_remove_tags():
    _, _, _, _, _, conn = create_load_balancer()

    lbs = conn.describe_load_balancers()["LoadBalancers"]
    assert len(lbs) == 1
    lb = lbs[0]

    with pytest.raises(ClientError):
        conn.add_tags(ResourceArns=["missing-arn"], Tags=[{"Key": "a", "Value": "b"}])

    conn.add_tags(
        ResourceArns=[lb["LoadBalancerArn"]], Tags=[{"Key": "a", "Value": "b"}]
    )

    tags = {
        d["Key"]: d["Value"]
        for d in conn.describe_tags(ResourceArns=[lb["LoadBalancerArn"]])[
            "TagDescriptions"
        ][0]["Tags"]
    }
    assert tags["a"] == "b"

    conn.add_tags(
        ResourceArns=[lb["LoadBalancerArn"]],
        Tags=[
            {"Key": "a", "Value": "b"},
            {"Key": "b", "Value": "b"},
            {"Key": "c", "Value": "b"},
            {"Key": "d", "Value": "b"},
            {"Key": "e", "Value": "b"},
            {"Key": "f", "Value": "b"},
            {"Key": "g", "Value": "b"},
            {"Key": "h", "Value": "b"},
            {"Key": "j", "Value": "b"},
        ],
    )

    with pytest.raises(ClientError) as exc:
        conn.add_tags(
            ResourceArns=[lb["LoadBalancerArn"]], Tags=[{"Key": "k", "Value": "b"}]
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "TooManyTagsError"

    conn.add_tags(
        ResourceArns=[lb["LoadBalancerArn"]], Tags=[{"Key": "j", "Value": "c"}]
    )

    tags = {
        d["Key"]: d["Value"]
        for d in conn.describe_tags(ResourceArns=[lb["LoadBalancerArn"]])[
            "TagDescriptions"
        ][0]["Tags"]
    }

    assert tags["a"] == "b"
    assert tags["b"] == "b"
    assert tags["c"] == "b"
    assert tags["d"] == "b"
    assert tags["e"] == "b"
    assert tags["f"] == "b"
    assert tags["g"] == "b"
    assert tags["h"] == "b"
    assert tags["j"] == "c"
    assert "k" not in tags

    conn.remove_tags(ResourceArns=[lb["LoadBalancerArn"]], TagKeys=["a"])

    tags = {
        d["Key"]: d["Value"]
        for d in conn.describe_tags(ResourceArns=[lb["LoadBalancerArn"]])[
            "TagDescriptions"
        ][0]["Tags"]
    }

    assert "a" not in tags
    assert tags["b"] == "b"
    assert tags["c"] == "b"
    assert tags["d"] == "b"
    assert tags["e"] == "b"
    assert tags["f"] == "b"
    assert tags["g"] == "b"
    assert tags["h"] == "b"
    assert tags["j"] == "c"


@mock_elbv2
@mock_ec2
def test_create_elb_in_multiple_region():
    for region in ["us-west-1", "us-west-2"]:
        conn = boto3.client("elbv2", region_name=region)
        ec2 = boto3.resource("ec2", region_name=region)

        security_group = ec2.create_security_group(
            GroupName="a-security-group", Description="First One"
        )
        vpc = ec2.create_vpc(CidrBlock="172.28.7.0/24", InstanceTenancy="default")
        subnet1 = ec2.create_subnet(
            VpcId=vpc.id, CidrBlock="172.28.7.0/26", AvailabilityZone=region + "a"
        )
        subnet2 = ec2.create_subnet(
            VpcId=vpc.id, CidrBlock="172.28.7.192/26", AvailabilityZone=region + "b"
        )

        conn.create_load_balancer(
            Name="my-lb",
            Subnets=[subnet1.id, subnet2.id],
            SecurityGroups=[security_group.id],
            Scheme="internal",
            Tags=[{"Key": "key_name", "Value": "a_value"}],
        )

    west_1_lbs = boto3.client("elbv2", "us-west-1").describe_load_balancers()
    assert len(west_1_lbs["LoadBalancers"]) == 1
    west_2_lbs = boto3.client("elbv2", "us-west-2").describe_load_balancers()
    assert len(west_2_lbs["LoadBalancers"]) == 1


@mock_elbv2
@mock_ec2
def test_create_listeners_without_port():
    response, vpc, _, _, _, conn = create_load_balancer()
    load_balancer_arn = response["LoadBalancers"][0]["LoadBalancerArn"]
    response = conn.create_target_group(
        Name="a-target",
        Protocol="HTTP",
        Port=8080,
        VpcId=vpc.id,
        HealthCheckProtocol="HTTP",
        HealthCheckPort="8080",
        HealthCheckPath="/",
        HealthCheckIntervalSeconds=5,
        HealthCheckTimeoutSeconds=3,
        HealthyThresholdCount=5,
        UnhealthyThresholdCount=2,
        Matcher={"HttpCode": "200"},
    )
    target_group = response["TargetGroups"][0]
    target_group_arn = target_group["TargetGroupArn"]
    response = conn.create_listener(
        LoadBalancerArn=load_balancer_arn,
        Protocol="HTTP",
        DefaultActions=[{"Type": "forward", "TargetGroupArn": target_group_arn}],
    )

    listener = response["Listeners"][0]
    assert listener.get("Port") is None
    assert listener["Protocol"] == "HTTP"
    assert listener["DefaultActions"] == [
        {"TargetGroupArn": target_group_arn, "Type": "forward"}
    ]


@mock_ec2
@mock_elbv2
def test_create_rule_forward_config_as_second_arg():
    # https://github.com/getmoto/moto/issues/4123
    # Necessary because there was some convoluted way of parsing arguments
    # Actions with type=forward had to be the first action specified
    response, vpc, _, _, _, elbv2 = create_load_balancer()

    load_balancer_arn = response["LoadBalancers"][0]["LoadBalancerArn"]

    response = elbv2.create_listener(
        LoadBalancerArn=load_balancer_arn, Protocol="HTTP", Port=80, DefaultActions=[]
    )
    http_listener_arn = response["Listeners"][0]["ListenerArn"]

    priority = 100

    response = elbv2.create_target_group(
        Name="a-target",
        Protocol="HTTP",
        Port=8080,
        VpcId=vpc.id,
        HealthCheckProtocol="HTTP",
        HealthCheckPort="8080",
        HealthCheckPath="/",
        Matcher={"HttpCode": "200"},
    )
    target_group = response["TargetGroups"][0]

    # No targets registered yet
    target_group_arn = target_group["TargetGroupArn"]
    elbv2.create_rule(
        ListenerArn=http_listener_arn,
        Conditions=[
            {"Field": "path-pattern", "PathPatternConfig": {"Values": ["/sth*"]}}
        ],
        Priority=priority,
        Actions=[
            {
                "Type": "authenticate-cognito",
                "Order": 1,
                "AuthenticateCognitoConfig": {
                    "UserPoolArn": "?1",
                    "UserPoolClientId": "?2",
                    "UserPoolDomain": "?2",
                    "SessionCookieName": "AWSELBAuthSessionCookie",
                    "Scope": "openid",
                    "SessionTimeout": 604800,
                    "OnUnauthenticatedRequest": "authenticate",
                },
            },
            {
                "Type": "forward",
                "Order": 2,
                "ForwardConfig": {
                    "TargetGroups": [
                        {"TargetGroupArn": target_group_arn, "Weight": 1},
                    ],
                    "TargetGroupStickinessConfig": {"Enabled": False},
                },
            },
        ],
    )
    all_rules = elbv2.describe_rules(ListenerArn=http_listener_arn)["Rules"]
    our_rule = all_rules[0]
    actions = our_rule["Actions"]
    forward_action = [a for a in actions if "ForwardConfig" in a.keys()][0]
    assert forward_action == {
        "ForwardConfig": {
            "TargetGroups": [{"TargetGroupArn": target_group_arn, "Weight": 1}],
            "TargetGroupStickinessConfig": {"Enabled": False},
        },
        "Type": "forward",
        "Order": 2,
    }


@mock_elbv2
@mock_ec2
def test_describe_paginated_balancers():
    conn = boto3.client("elbv2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    security_group = ec2.create_security_group(
        GroupName="a-security-group", Description="First One"
    )
    vpc = ec2.create_vpc(CidrBlock="172.28.7.0/24", InstanceTenancy="default")
    subnet1 = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="172.28.7.192/26", AvailabilityZone="us-east-1a"
    )
    subnet2 = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="172.28.7.0/26", AvailabilityZone="us-east-1b"
    )

    for i in range(51):
        conn.create_load_balancer(
            Name=f"my-lb{i}",
            Subnets=[subnet1.id, subnet2.id],
            SecurityGroups=[security_group.id],
            Scheme="internal",
            Tags=[{"Key": "key_name", "Value": "a_value"}],
        )

    resp = conn.describe_load_balancers()
    assert len(resp["LoadBalancers"]) == 50
    assert resp["NextMarker"] == resp["LoadBalancers"][-1]["LoadBalancerName"]
    resp2 = conn.describe_load_balancers(Marker=resp["NextMarker"])
    assert len(resp2["LoadBalancers"]) == 1
    assert "NextToken" not in resp2.keys()


@mock_elbv2
@mock_ec2
def test_delete_load_balancer():
    response, _, _, _, _, conn = create_load_balancer()

    assert len(response["LoadBalancers"]) == 1
    lb = response["LoadBalancers"][0]

    conn.delete_load_balancer(LoadBalancerArn=lb["LoadBalancerArn"])
    balancers = conn.describe_load_balancers()["LoadBalancers"]
    assert len(balancers) == 0


@mock_ec2
@mock_elbv2
def test_register_targets():
    conn = boto3.client("elbv2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    security_group = ec2.create_security_group(
        GroupName="a-security-group", Description="First One"
    )
    vpc = ec2.create_vpc(CidrBlock="172.28.7.0/24", InstanceTenancy="default")
    subnet1 = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="172.28.7.192/26", AvailabilityZone="us-east-1a"
    )
    subnet2 = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="172.28.7.0/26", AvailabilityZone="us-east-1b"
    )

    conn.create_load_balancer(
        Name="my-lb",
        Subnets=[subnet1.id, subnet2.id],
        SecurityGroups=[security_group.id],
        Scheme="internal",
        Tags=[{"Key": "key_name", "Value": "a_value"}],
    )

    response = conn.create_target_group(
        Name="a-target",
        Protocol="HTTP",
        Port=8080,
        VpcId=vpc.id,
        HealthCheckProtocol="HTTP",
        HealthCheckPort="8080",
        HealthCheckPath="/",
        HealthCheckIntervalSeconds=5,
        HealthCheckTimeoutSeconds=3,
        HealthyThresholdCount=5,
        UnhealthyThresholdCount=2,
        Matcher={"HttpCode": "200"},
    )
    target_group = response["TargetGroups"][0]

    # No targets registered yet
    response = conn.describe_target_health(
        TargetGroupArn=target_group["TargetGroupArn"]
    )
    assert len(response["TargetHealthDescriptions"]) == 0

    response = ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=2, MaxCount=2)
    instance_id1 = response[0].id
    instance_id2 = response[1].id

    response = conn.register_targets(
        TargetGroupArn=target_group["TargetGroupArn"],
        Targets=[
            {"Id": instance_id1, "Port": 5060},
            {"Id": instance_id2, "Port": 4030},
        ],
    )

    response = conn.describe_target_health(
        TargetGroupArn=target_group["TargetGroupArn"]
    )
    assert len(response["TargetHealthDescriptions"]) == 2

    response = conn.deregister_targets(
        TargetGroupArn=target_group["TargetGroupArn"],
        Targets=[{"Id": instance_id2}],
    )

    response = conn.describe_target_health(
        TargetGroupArn=target_group["TargetGroupArn"]
    )
    assert len(response["TargetHealthDescriptions"]) == 1

    def get_target_by_instance_id(instance_id):
        for target in response["TargetHealthDescriptions"]:
            if target["Target"]["Id"] == instance_id:
                return target
        return None

    def assert_target_not_registered(target):
        assert target["TargetHealth"]["State"] == "unavailable"
        assert target["TargetHealth"]["Reason"] == "Target.NotRegistered"

    response = conn.describe_target_health(
        TargetGroupArn=target_group["TargetGroupArn"],
        Targets=[{"Id": instance_id2}],
    )
    assert len(response["TargetHealthDescriptions"]) == 1
    target_default_port = get_target_by_instance_id(instance_id2)
    assert target_default_port is not None
    assert target_default_port["Target"]["Port"] == 8080
    assert_target_not_registered(target_default_port)

    response = conn.describe_target_health(
        TargetGroupArn=target_group["TargetGroupArn"],
        Targets=[{"Id": instance_id2, "Port": 4030}],
    )
    assert len(response["TargetHealthDescriptions"]) == 1
    target_custom_port = get_target_by_instance_id(instance_id2)
    assert target_custom_port is not None
    assert target_custom_port["Target"]["Port"] == 4030
    assert_target_not_registered(target_custom_port)


@mock_ec2
@mock_elbv2
def test_stopped_instance_target():
    target_group_port = 8080

    conn = boto3.client("elbv2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    security_group = ec2.create_security_group(
        GroupName="a-security-group", Description="First One"
    )
    vpc = ec2.create_vpc(CidrBlock="172.28.7.0/24", InstanceTenancy="default")
    subnet1 = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="172.28.7.192/26", AvailabilityZone="us-east-1a"
    )
    subnet2 = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="172.28.7.0/26", AvailabilityZone="us-east-1b"
    )

    conn.create_load_balancer(
        Name="my-lb",
        Subnets=[subnet1.id, subnet2.id],
        SecurityGroups=[security_group.id],
        Scheme="internal",
        Tags=[{"Key": "key_name", "Value": "a_value"}],
    )

    response = conn.create_target_group(
        Name="a-target",
        Protocol="HTTP",
        Port=target_group_port,
        VpcId=vpc.id,
        HealthCheckProtocol="HTTP",
        HealthCheckPath="/",
        HealthCheckIntervalSeconds=5,
        HealthCheckTimeoutSeconds=3,
        HealthyThresholdCount=5,
        UnhealthyThresholdCount=2,
        Matcher={"HttpCode": "200"},
    )
    target_group = response["TargetGroups"][0]

    # No targets registered yet
    response = conn.describe_target_health(
        TargetGroupArn=target_group["TargetGroupArn"]
    )
    assert len(response["TargetHealthDescriptions"]) == 0

    response = ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    instance = response[0]

    target_dict = {"Id": instance.id, "Port": 500}

    response = conn.register_targets(
        TargetGroupArn=target_group["TargetGroupArn"], Targets=[target_dict]
    )

    response = conn.describe_target_health(
        TargetGroupArn=target_group["TargetGroupArn"]
    )
    assert len(response["TargetHealthDescriptions"]) == 1
    target_health_description = response["TargetHealthDescriptions"][0]

    assert target_health_description["Target"] == target_dict
    assert target_health_description["HealthCheckPort"] == "traffic-port"
    assert target_health_description["TargetHealth"] == {"State": "healthy"}

    instance.stop()

    response = conn.describe_target_health(
        TargetGroupArn=target_group["TargetGroupArn"]
    )
    assert len(response["TargetHealthDescriptions"]) == 1
    target_health_description = response["TargetHealthDescriptions"][0]
    assert target_health_description["Target"] == target_dict
    assert target_health_description["HealthCheckPort"] == "traffic-port"
    assert target_health_description["TargetHealth"] == {
        "State": "unused",
        "Reason": "Target.InvalidState",
        "Description": "Target is in the stopped state",
    }


@mock_ec2
@mock_elbv2
def test_terminated_instance_target():
    target_group_port = 8080

    conn = boto3.client("elbv2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    security_group = ec2.create_security_group(
        GroupName="a-security-group", Description="First One"
    )
    vpc = ec2.create_vpc(CidrBlock="172.28.7.0/24", InstanceTenancy="default")
    subnet1 = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="172.28.7.192/26", AvailabilityZone="us-east-1a"
    )
    subnet2 = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="172.28.7.0/26", AvailabilityZone="us-east-1b"
    )

    conn.create_load_balancer(
        Name="my-lb",
        Subnets=[subnet1.id, subnet2.id],
        SecurityGroups=[security_group.id],
        Scheme="internal",
        Tags=[{"Key": "key_name", "Value": "a_value"}],
    )

    response = conn.create_target_group(
        Name="a-target",
        Protocol="HTTP",
        Port=target_group_port,
        VpcId=vpc.id,
        HealthCheckProtocol="HTTP",
        HealthCheckPath="/",
        HealthCheckIntervalSeconds=5,
        HealthCheckTimeoutSeconds=3,
        HealthyThresholdCount=5,
        UnhealthyThresholdCount=2,
        Matcher={"HttpCode": "200"},
    )
    target_group = response["TargetGroups"][0]

    # No targets registered yet
    response = conn.describe_target_health(
        TargetGroupArn=target_group["TargetGroupArn"]
    )
    assert len(response["TargetHealthDescriptions"]) == 0

    response = ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    instance = response[0]

    target_dict = {"Id": instance.id, "Port": 500}

    response = conn.register_targets(
        TargetGroupArn=target_group["TargetGroupArn"], Targets=[target_dict]
    )

    response = conn.describe_target_health(
        TargetGroupArn=target_group["TargetGroupArn"]
    )
    assert len(response["TargetHealthDescriptions"]) == 1
    target_health_description = response["TargetHealthDescriptions"][0]

    assert target_health_description["Target"] == target_dict
    assert target_health_description["HealthCheckPort"] == "traffic-port"
    assert target_health_description["TargetHealth"] == {"State": "healthy"}

    instance.terminate()

    response = conn.describe_target_health(
        TargetGroupArn=target_group["TargetGroupArn"]
    )
    assert len(response["TargetHealthDescriptions"]) == 0


@mock_elbv2
@mock_ec2
def test_create_rule_priority_in_use():
    response, _, _, _, _, elbv2 = create_load_balancer()

    load_balancer_arn = response["LoadBalancers"][0]["LoadBalancerArn"]

    response = elbv2.create_listener(
        LoadBalancerArn=load_balancer_arn, Protocol="HTTP", Port=80, DefaultActions=[]
    )
    http_listener_arn = response["Listeners"][0]["ListenerArn"]

    priority = 100
    elbv2.create_rule(
        ListenerArn=http_listener_arn, Priority=priority, Conditions=[], Actions=[]
    )

    # test for PriorityInUse
    with pytest.raises(ClientError) as ex:
        elbv2.create_rule(
            ListenerArn=http_listener_arn, Priority=priority, Conditions=[], Actions=[]
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "PriorityInUse"
    assert err["Message"] == "The specified priority is in use."


@mock_elbv2
@mock_ec2
def test_modify_rule_conditions():
    response, _, _, _, _, elbv2 = create_load_balancer()
    load_balancer_arn = response["LoadBalancers"][0]["LoadBalancerArn"]

    action = {
        "Type": "redirect",
        "RedirectConfig": {
            "Protocol": "HTTPS",
            "Port": "443",
            "StatusCode": "HTTP_301",
        },
    }
    condition = {"Field": "path-pattern", "PathPatternConfig": {"Values": ["/sth*"]}}

    response = elbv2.create_listener(
        LoadBalancerArn=load_balancer_arn,
        Protocol="HTTP",
        Port=80,
        DefaultActions=[action],
    )
    http_listener_arn = response["Listeners"][0]["ListenerArn"]

    response = elbv2.create_rule(
        ListenerArn=http_listener_arn, Priority=100, Conditions=[], Actions=[]
    )
    rule = response["Rules"][0]

    assert len(rule["Actions"]) == 0
    assert len(rule["Conditions"]) == 0

    response = elbv2.modify_rule(RuleArn=rule["RuleArn"], Actions=[action])
    rule = response["Rules"][0]

    assert len(rule["Actions"]) == 1
    assert len(rule["Conditions"]) == 0

    response = elbv2.modify_rule(RuleArn=rule["RuleArn"], Conditions=[condition])
    rule = response["Rules"][0]

    assert len(rule["Actions"]) == 1
    assert len(rule["Conditions"]) == 1

    response = elbv2.modify_rule(
        RuleArn=rule["RuleArn"],
        Conditions=[condition, condition],
        Actions=[action, action],
    )
    rule = response["Rules"][0]

    assert len(rule["Actions"]) == 2
    assert len(rule["Conditions"]) == 2


@mock_elbv2
@mock_ec2
def test_handle_listener_rules():
    response, vpc, _, _, _, conn = create_load_balancer()

    load_balancer_arn = response["LoadBalancers"][0]["LoadBalancerArn"]

    response = conn.create_target_group(
        Name="a-target",
        Protocol="HTTP",
        Port=8080,
        VpcId=vpc.id,
        HealthCheckProtocol="HTTP",
        HealthCheckPort="8080",
        HealthCheckPath="/",
        HealthCheckIntervalSeconds=5,
        HealthCheckTimeoutSeconds=3,
        HealthyThresholdCount=5,
        UnhealthyThresholdCount=2,
        Matcher={"HttpCode": "200"},
    )
    target_group = response["TargetGroups"][0]

    # Plain HTTP listener
    response = conn.create_listener(
        LoadBalancerArn=load_balancer_arn,
        Protocol="HTTP",
        Port=80,
        DefaultActions=[
            {"Type": "forward", "TargetGroupArn": target_group["TargetGroupArn"]}
        ],
    )
    listener = response["Listeners"][0]
    assert listener["Port"] == 80
    assert listener["Protocol"] == "HTTP"
    assert listener["DefaultActions"] == [
        {"TargetGroupArn": target_group["TargetGroupArn"], "Type": "forward"}
    ]
    http_listener_arn = listener["ListenerArn"]

    # create first rule
    priority = 100
    host = "xxx.example.com"
    path_pattern = "foobar"
    pathpatternconfig_pattern = "foobar2"
    created_rule = conn.create_rule(
        ListenerArn=http_listener_arn,
        Priority=priority,
        Conditions=[
            {"Field": "host-header", "Values": [host]},
            {"Field": "path-pattern", "Values": [path_pattern]},
            {
                "Field": "path-pattern",
                "PathPatternConfig": {"Values": [pathpatternconfig_pattern]},
            },
        ],
        Actions=[{"TargetGroupArn": target_group["TargetGroupArn"], "Type": "forward"}],
    )
    rule = created_rule["Rules"][0]
    assert rule["Priority"] == "100"

    # check if rules is sorted by priority
    priority = 500
    host = "yyy.example.com"
    path_pattern = "foobar"
    rules = conn.create_rule(
        ListenerArn=http_listener_arn,
        Priority=priority,
        Conditions=[
            {"Field": "host-header", "Values": [host]},
            {"Field": "path-pattern", "Values": [path_pattern]},
            {
                "Field": "path-pattern",
                "PathPatternConfig": {"Values": [pathpatternconfig_pattern]},
            },
        ],
        Actions=[{"TargetGroupArn": target_group["TargetGroupArn"], "Type": "forward"}],
    )

    # add rule that uses forward_config
    priority = 550
    host = "aaa.example.com"
    path_pattern = "barfoo"
    rules = conn.create_rule(
        ListenerArn=http_listener_arn,
        Priority=priority,
        Conditions=[
            {"Field": "host-header", "Values": [host]},
            {"Field": "path-pattern", "Values": [path_pattern]},
            {
                "Field": "path-pattern",
                "PathPatternConfig": {"Values": [pathpatternconfig_pattern]},
            },
        ],
        Actions=[
            {
                "Type": "forward",
                "ForwardConfig": {
                    "TargetGroups": [
                        {
                            "TargetGroupArn": target_group["TargetGroupArn"],
                            "Weight": 1,
                        },
                        {
                            "TargetGroupArn": target_group["TargetGroupArn"],
                            "Weight": 2,
                        },
                    ]
                },
            },
        ],
    )

    # test for PriorityInUse
    with pytest.raises(ClientError):
        conn.create_rule(
            ListenerArn=http_listener_arn,
            Priority=priority,
            Conditions=[
                {"Field": "host-header", "Values": [host]},
                {"Field": "path-pattern", "Values": [path_pattern]},
                {
                    "Field": "path-pattern",
                    "PathPatternConfig": {"Values": [pathpatternconfig_pattern]},
                },
            ],
            Actions=[
                {
                    "TargetGroupArn": target_group["TargetGroupArn"],
                    "Type": "forward",
                }
            ],
        )

    # test for describe listeners
    obtained_rules = conn.describe_rules(ListenerArn=http_listener_arn)
    assert len(obtained_rules["Rules"]) == 4
    priorities = [rule["Priority"] for rule in obtained_rules["Rules"]]
    assert priorities == ["100", "500", "550", "default"]

    first_rule = obtained_rules["Rules"][0]
    second_rule = obtained_rules["Rules"][1]
    third_rule = obtained_rules["Rules"][2]
    default_rule = obtained_rules["Rules"][3]
    assert first_rule["IsDefault"] is False
    assert default_rule["IsDefault"] is True
    obtained_rules = conn.describe_rules(RuleArns=[first_rule["RuleArn"]])
    assert obtained_rules["Rules"] == [first_rule]

    # test for pagination
    obtained_rules = conn.describe_rules(ListenerArn=http_listener_arn, PageSize=1)
    assert len(obtained_rules["Rules"]) == 1
    next_marker = obtained_rules["NextMarker"]

    following_rules = conn.describe_rules(
        ListenerArn=http_listener_arn, PageSize=1, Marker=next_marker
    )
    assert len(following_rules["Rules"]) == 1
    assert (
        following_rules["Rules"][0]["RuleArn"] != obtained_rules["Rules"][0]["RuleArn"]
    )

    # test for invalid describe rule request
    with pytest.raises(ClientError):
        conn.describe_rules()
    with pytest.raises(ClientError):
        conn.describe_rules(RuleArns=[])
    with pytest.raises(ClientError):
        conn.describe_rules(
            ListenerArn=http_listener_arn, RuleArns=[first_rule["RuleArn"]]
        )

    # modify rule partially
    new_host = "new.example.com"
    new_path_pattern = "new_path"
    new_pathpatternconfig_pattern = "new_path2"
    conn.modify_rule(
        RuleArn=first_rule["RuleArn"],
        Conditions=[
            {"Field": "host-header", "Values": [new_host]},
            {"Field": "path-pattern", "Values": [new_path_pattern]},
            {
                "Field": "path-pattern",
                "PathPatternConfig": {"Values": [new_pathpatternconfig_pattern]},
            },
        ],
    )

    rules = conn.describe_rules(ListenerArn=http_listener_arn)
    obtained_rule = rules["Rules"][0]
    assert obtained_rule["Conditions"][0]["Values"][0] == new_host
    assert obtained_rule["Conditions"][1]["Values"][0] == new_path_pattern
    assert (
        obtained_rule["Conditions"][2]["PathPatternConfig"]["Values"][0]
        == new_pathpatternconfig_pattern
    )
    assert (
        obtained_rule["Actions"][0]["TargetGroupArn"] == target_group["TargetGroupArn"]
    )

    # modify priority
    new_priority = int(first_rule["Priority"]) - 1
    updated_rule = conn.set_rule_priorities(
        RulePriorities=[
            {
                "RuleArn": first_rule["RuleArn"],
                "Priority": new_priority,
            }
        ]
    )

    # assert response of SetRulePriorities operation
    assert len(updated_rule["Rules"]) == 1
    assert updated_rule["Rules"][0]["RuleArn"] == first_rule["RuleArn"]
    assert updated_rule["Rules"][0]["Priority"] == str(new_priority)
    assert len(updated_rule["Rules"][0]["Conditions"]) == 3
    assert len(updated_rule["Rules"][0]["Actions"]) == 1

    # modify forward_config rule partially rule
    new_host_2 = "new.examplewebsite.com"
    new_path_pattern_2 = "new_path_2"
    new_pathpatternconfig_pattern_2 = "new_path_2"
    conn.modify_rule(
        RuleArn=third_rule["RuleArn"],
        Conditions=[
            {"Field": "host-header", "Values": [new_host_2]},
            {"Field": "path-pattern", "Values": [new_path_pattern_2]},
            {
                "Field": "path-pattern",
                "PathPatternConfig": {"Values": [new_pathpatternconfig_pattern_2]},
            },
        ],
        Actions=[{"TargetGroupArn": target_group["TargetGroupArn"], "Type": "forward"}],
    )

    rules = conn.describe_rules(ListenerArn=http_listener_arn)
    obtained_rule = rules["Rules"][2]
    assert obtained_rule["Conditions"][0]["Values"][0] == new_host_2
    assert obtained_rule["Conditions"][1]["Values"][0] == new_path_pattern_2
    assert (
        obtained_rule["Conditions"][2]["PathPatternConfig"]["Values"][0]
        == new_pathpatternconfig_pattern_2
    )
    assert (
        obtained_rule["Actions"][0]["TargetGroupArn"] == target_group["TargetGroupArn"]
    )

    # modify priority
    conn.set_rule_priorities(
        RulePriorities=[
            {
                "RuleArn": third_rule["RuleArn"],
                "Priority": int(third_rule["Priority"]) - 1,
            }
        ]
    )

    with pytest.raises(ClientError):
        conn.set_rule_priorities(
            RulePriorities=[
                {"RuleArn": first_rule["RuleArn"], "Priority": 999},
                {"RuleArn": second_rule["RuleArn"], "Priority": 999},
                {"RuleArn": third_rule["RuleArn"], "Priority": 999},
            ]
        )

    # delete
    arn = first_rule["RuleArn"]
    conn.delete_rule(RuleArn=arn)
    rules = conn.describe_rules(ListenerArn=http_listener_arn)["Rules"]
    assert len(rules) == 3

    # test for invalid action type
    safe_priority = 2
    with pytest.raises(ClientError):
        conn.create_rule(
            ListenerArn=http_listener_arn,
            Priority=safe_priority,
            Conditions=[
                {"Field": "host-header", "Values": [host]},
                {"Field": "path-pattern", "Values": [path_pattern]},
            ],
            Actions=[
                {
                    "TargetGroupArn": target_group["TargetGroupArn"],
                    "Type": "forward2",
                }
            ],
        )

    # test for invalid action type
    safe_priority = 2
    invalid_target_group_arn = target_group["TargetGroupArn"] + "x"
    with pytest.raises(ClientError):
        conn.create_rule(
            ListenerArn=http_listener_arn,
            Priority=safe_priority,
            Conditions=[
                {"Field": "host-header", "Values": [host]},
                {"Field": "path-pattern", "Values": [path_pattern]},
            ],
            Actions=[{"TargetGroupArn": invalid_target_group_arn, "Type": "forward"}],
        )

    # test for invalid condition field_name
    safe_priority = 2
    with pytest.raises(ClientError):
        conn.create_rule(
            ListenerArn=http_listener_arn,
            Priority=safe_priority,
            Conditions=[{"Field": "xxxxxxx", "Values": [host]}],
            Actions=[
                {
                    "TargetGroupArn": target_group["TargetGroupArn"],
                    "Type": "forward",
                }
            ],
        )

    # test for emptry condition value
    safe_priority = 2
    with pytest.raises(ClientError):
        conn.create_rule(
            ListenerArn=http_listener_arn,
            Priority=safe_priority,
            Conditions=[{"Field": "host-header", "Values": []}],
            Actions=[
                {
                    "TargetGroupArn": target_group["TargetGroupArn"],
                    "Type": "forward",
                }
            ],
        )

    # test for multiple condition value
    safe_priority = 2
    with pytest.raises(ClientError):
        conn.create_rule(
            ListenerArn=http_listener_arn,
            Priority=safe_priority,
            Conditions=[{"Field": "host-header", "Values": [host, host]}],
            Actions=[
                {
                    "TargetGroupArn": target_group["TargetGroupArn"],
                    "Type": "forward",
                }
            ],
        )


@mock_elbv2
def test_describe_account_limits():
    client = boto3.client("elbv2", region_name="eu-central-1")

    resp = client.describe_account_limits()
    assert "Name" in resp["Limits"][0]
    assert "Max" in resp["Limits"][0]


@mock_elbv2
def test_describe_ssl_policies():
    client = boto3.client("elbv2", region_name="eu-central-1")

    resp = client.describe_ssl_policies()
    assert len(resp["SslPolicies"]) > 0

    resp = client.describe_ssl_policies(
        Names=["ELBSecurityPolicy-TLS-1-2-2017-01", "ELBSecurityPolicy-2016-08"]
    )
    assert len(resp["SslPolicies"]) == 2

    resp = client.describe_ssl_policies(
        Names=[
            "ELBSecurityPolicy-TLS-1-2-2017-01",
            "ELBSecurityPolicy-2016-08",
            "ELBSecurityPolicy-2016-08",
        ]
    )
    assert len(resp["SslPolicies"]) == 2


@mock_elbv2
@mock_ec2
def test_set_ip_address_type():
    response, _, security_group, subnet1, subnet2, client = create_load_balancer()
    arn = response["LoadBalancers"][0]["LoadBalancerArn"]

    # Internal LBs cant be dualstack yet
    with pytest.raises(ClientError):
        client.set_ip_address_type(LoadBalancerArn=arn, IpAddressType="dualstack")

    # Create internet facing one
    response = client.create_load_balancer(
        Name="my-lb2",
        Subnets=[subnet1.id, subnet2.id],
        SecurityGroups=[security_group.id],
        Scheme="internet-facing",
        Tags=[{"Key": "key_name", "Value": "a_value"}],
    )
    arn = response["LoadBalancers"][0]["LoadBalancerArn"]

    client.set_ip_address_type(LoadBalancerArn=arn, IpAddressType="dualstack")

    with pytest.raises(ClientError) as ex:
        client.set_ip_address_type(LoadBalancerArn=arn, IpAddressType="internal")
    err = ex.value.response["Error"]
    assert err["Code"] == "ValidationError"


@mock_elbv2
@mock_ec2
def test_set_security_groups():
    client = boto3.client("elbv2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    security_group = ec2.create_security_group(
        GroupName="a-security-group", Description="First One"
    )
    security_group2 = ec2.create_security_group(
        GroupName="b-security-group", Description="Second One"
    )
    vpc = ec2.create_vpc(CidrBlock="172.28.7.0/24", InstanceTenancy="default")
    subnet1 = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="172.28.7.192/26", AvailabilityZone="us-east-1a"
    )
    subnet2 = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="172.28.7.0/26", AvailabilityZone="us-east-1b"
    )

    response = client.create_load_balancer(
        Name="my-lb",
        Subnets=[subnet1.id, subnet2.id],
        SecurityGroups=[security_group.id],
        Scheme="internal",
        Tags=[{"Key": "key_name", "Value": "a_value"}],
    )
    arn = response["LoadBalancers"][0]["LoadBalancerArn"]

    client.set_security_groups(
        LoadBalancerArn=arn, SecurityGroups=[security_group.id, security_group2.id]
    )

    resp = client.describe_load_balancers(LoadBalancerArns=[arn])
    assert len(resp["LoadBalancers"][0]["SecurityGroups"]) == 2

    with pytest.raises(ClientError):
        client.set_security_groups(LoadBalancerArn=arn, SecurityGroups=["non_existent"])


@mock_elbv2
@mock_ec2
def test_modify_load_balancer_attributes_idle_timeout():
    response, _, _, _, _, client = create_load_balancer()
    arn = response["LoadBalancers"][0]["LoadBalancerArn"]

    client.modify_load_balancer_attributes(
        LoadBalancerArn=arn,
        Attributes=[{"Key": "idle_timeout.timeout_seconds", "Value": "600"}],
    )

    # Check its 600 not 60
    response = client.describe_load_balancer_attributes(LoadBalancerArn=arn)
    idle_timeout = list(
        filter(
            lambda item: item["Key"] == "idle_timeout.timeout_seconds",
            response["Attributes"],
        )
    )[0]
    assert idle_timeout["Value"] == "600"


@mock_elbv2
@mock_ec2
def test_modify_load_balancer_attributes_routing_http2_enabled():
    response, _, _, _, _, client = create_load_balancer()
    arn = response["LoadBalancers"][0]["LoadBalancerArn"]

    client.modify_load_balancer_attributes(
        LoadBalancerArn=arn,
        Attributes=[{"Key": "routing.http2.enabled", "Value": "false"}],
    )

    response = client.describe_load_balancer_attributes(LoadBalancerArn=arn)
    routing_http2_enabled = list(
        filter(
            lambda item: item["Key"] == "routing.http2.enabled", response["Attributes"]
        )
    )[0]
    assert routing_http2_enabled["Value"] == "false"


@mock_elbv2
@mock_ec2
def test_modify_load_balancer_attributes_crosszone_enabled():
    response, _, _, _, _, client = create_load_balancer()
    arn = response["LoadBalancers"][0]["LoadBalancerArn"]

    client.modify_load_balancer_attributes(
        LoadBalancerArn=arn,
        Attributes=[
            {"Key": "load_balancing.cross_zone.enabled", "Value": "false"},
            {"Key": "deletion_protection.enabled", "Value": "false"},
        ],
    )

    attrs = client.describe_load_balancer_attributes(LoadBalancerArn=arn)["Attributes"]
    assert {"Key": "deletion_protection.enabled", "Value": "false"} in attrs
    assert {"Key": "load_balancing.cross_zone.enabled", "Value": "false"} in attrs


@mock_elbv2
@mock_ec2
def test_modify_load_balancer_attributes_routing_http_drop_invalid_header_fields_enabled():
    response, _, _, _, _, client = create_load_balancer()
    arn = response["LoadBalancers"][0]["LoadBalancerArn"]

    client.modify_load_balancer_attributes(
        LoadBalancerArn=arn,
        Attributes=[
            {"Key": "routing.http.drop_invalid_header_fields.enabled", "Value": "false"}
        ],
    )

    response = client.describe_load_balancer_attributes(LoadBalancerArn=arn)
    routing_http_drop_invalid_header_fields_enabled = list(
        filter(
            lambda item: item["Key"]
            == "routing.http.drop_invalid_header_fields.enabled",
            response["Attributes"],
        )
    )[0]
    assert routing_http_drop_invalid_header_fields_enabled["Value"] == "false"


@mock_elbv2
@mock_ec2
@mock_acm
def test_modify_listener_http_to_https():
    client = boto3.client("elbv2", region_name="eu-central-1")
    acm = boto3.client("acm", region_name="eu-central-1")
    ec2 = boto3.resource("ec2", region_name="eu-central-1")

    security_group = ec2.create_security_group(
        GroupName="a-security-group", Description="First One"
    )
    vpc = ec2.create_vpc(CidrBlock="172.28.7.0/24", InstanceTenancy="default")
    subnet1 = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="172.28.7.192/26", AvailabilityZone="eu-central-1a"
    )
    subnet2 = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="172.28.7.0/26", AvailabilityZone="eu-central-1b"
    )

    response = client.create_load_balancer(
        Name="my-lb",
        Subnets=[subnet1.id, subnet2.id],
        SecurityGroups=[security_group.id],
        Scheme="internal",
        Tags=[{"Key": "key_name", "Value": "a_value"}],
    )

    load_balancer_arn = response["LoadBalancers"][0]["LoadBalancerArn"]

    response = client.create_target_group(
        Name="a-target",
        Protocol="HTTP",
        Port=8080,
        VpcId=vpc.id,
        HealthCheckProtocol="HTTP",
        HealthCheckPort="8080",
        HealthCheckPath="/",
        HealthCheckIntervalSeconds=5,
        HealthCheckTimeoutSeconds=3,
        HealthyThresholdCount=5,
        UnhealthyThresholdCount=2,
        Matcher={"HttpCode": "200"},
    )
    target_group = response["TargetGroups"][0]
    target_group_arn = target_group["TargetGroupArn"]

    # Plain HTTP listener
    response = client.create_listener(
        LoadBalancerArn=load_balancer_arn,
        Protocol="HTTP",
        Port=80,
        DefaultActions=[{"Type": "forward", "TargetGroupArn": target_group_arn}],
    )
    listener_arn = response["Listeners"][0]["ListenerArn"]

    # No default cert
    with pytest.raises(ClientError) as ex:
        client.modify_listener(
            ListenerArn=listener_arn,
            Port=443,
            Protocol="HTTPS",
            SslPolicy="ELBSecurityPolicy-TLS-1-2-2017-01",
            Certificates=[],
            DefaultActions=[{"Type": "forward", "TargetGroupArn": target_group_arn}],
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "CertificateWereNotPassed"
    assert (
        err["Message"]
        == "You must provide a list containing exactly one certificate if the listener protocol is HTTPS."
    )

    acm.request_certificate(
        DomainName="google.com",
        SubjectAlternativeNames=["google.com", "www.google.com", "mail.google.com"],
    )
    response = acm.request_certificate(
        DomainName="yahoo.com",
        SubjectAlternativeNames=["yahoo.com", "www.yahoo.com", "mail.yahoo.com"],
    )
    yahoo_arn = response["CertificateArn"]

    response = client.modify_listener(
        ListenerArn=listener_arn,
        Port=443,
        Protocol="HTTPS",
        SslPolicy="ELBSecurityPolicy-TLS-1-2-2017-01",
        Certificates=[{"CertificateArn": yahoo_arn}],
        DefaultActions=[{"Type": "forward", "TargetGroupArn": target_group_arn}],
    )
    assert response["Listeners"][0]["Port"] == 443
    assert response["Listeners"][0]["Protocol"] == "HTTPS"
    assert response["Listeners"][0]["SslPolicy"] == "ELBSecurityPolicy-TLS-1-2-2017-01"
    assert len(response["Listeners"][0]["Certificates"]) == 1

    # Check default cert, can't do this in server mode
    if os.environ.get("TEST_SERVER_MODE", "false").lower() == "false":
        listener = (
            elbv2_backends[ACCOUNT_ID]["eu-central-1"]
            .load_balancers[load_balancer_arn]
            .listeners[listener_arn]
        )
        assert listener.certificate == yahoo_arn

    # Bad cert
    with pytest.raises(ClientError) as exc:
        client.modify_listener(
            ListenerArn=listener_arn,
            Port=443,
            Protocol="HTTPS",
            SslPolicy="ELBSecurityPolicy-TLS-1-2-2017-01",
            Certificates=[{"CertificateArn": "lalala", "IsDefault": True}],
            DefaultActions=[{"Type": "forward", "TargetGroupArn": target_group_arn}],
        )
    err = exc.value.response["Error"]
    assert err["Message"] == "Certificate lalala not found"

    # Unknown protocol
    with pytest.raises(ClientError) as exc:
        client.modify_listener(
            ListenerArn=listener_arn,
            Port=443,
            Protocol="HTP",
            SslPolicy="ELBSecurityPolicy-TLS-1-2-2017-01",
            Certificates=[{"CertificateArn": yahoo_arn, "IsDefault": True}],
            DefaultActions=[{"Type": "forward", "TargetGroupArn": target_group_arn}],
        )
    err = exc.value.response["Error"]
    assert err["Message"] == "Protocol HTP is not supported"


@mock_acm
@mock_ec2
@mock_elbv2
def test_modify_listener_of_https_target_group():
    # Verify we can add a listener for a TargetGroup that is already HTTPS
    client = boto3.client("elbv2", region_name="eu-central-1")
    acm = boto3.client("acm", region_name="eu-central-1")
    ec2 = boto3.resource("ec2", region_name="eu-central-1")

    security_group = ec2.create_security_group(
        GroupName="a-security-group", Description="First One"
    )
    vpc = ec2.create_vpc(CidrBlock="172.28.7.0/24", InstanceTenancy="default")
    subnet1 = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="172.28.7.192/26", AvailabilityZone="eu-central-1a"
    )

    response = client.create_load_balancer(
        Name="my-lb",
        Subnets=[subnet1.id],
        SecurityGroups=[security_group.id],
        Scheme="internal",
        Tags=[{"Key": "key_name", "Value": "a_value"}],
    )

    load_balancer_arn = response["LoadBalancers"][0]["LoadBalancerArn"]

    response = client.create_target_group(
        Name="a-target", Protocol="HTTPS", Port=8443, VpcId=vpc.id
    )
    target_group = response["TargetGroups"][0]
    target_group_arn = target_group["TargetGroupArn"]

    # HTTPS listener
    response = acm.request_certificate(
        DomainName="google.com", SubjectAlternativeNames=["google.com"]
    )
    google_arn = response["CertificateArn"]
    response = client.create_listener(
        LoadBalancerArn=load_balancer_arn,
        Protocol="HTTPS",
        Port=443,
        Certificates=[{"CertificateArn": google_arn}],
        DefaultActions=[{"Type": "forward", "TargetGroupArn": target_group_arn}],
    )
    listener_arn = response["Listeners"][0]["ListenerArn"]

    # Now modify the HTTPS listener with a different certificate
    response = acm.request_certificate(
        DomainName="yahoo.com", SubjectAlternativeNames=["yahoo.com"]
    )
    yahoo_arn = response["CertificateArn"]

    listener = client.modify_listener(
        ListenerArn=listener_arn,
        Certificates=[{"CertificateArn": yahoo_arn}],
        DefaultActions=[{"Type": "forward", "TargetGroupArn": target_group_arn}],
    )["Listeners"][0]
    assert listener["Certificates"] == [{"CertificateArn": yahoo_arn}]

    listener = client.describe_listeners(ListenerArns=[listener_arn])["Listeners"][0]
    assert listener["Certificates"] == [{"CertificateArn": yahoo_arn}]


@mock_elbv2
def test_add_unknown_listener_certificate():
    client = boto3.client("elbv2", region_name="eu-central-1")
    with pytest.raises(ClientError) as exc:
        client.add_listener_certificates(
            ListenerArn="unknown", Certificates=[{"CertificateArn": "google_arn"}]
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ListenerNotFound"


@mock_elbv2
def test_describe_unknown_listener_certificate():
    client = boto3.client("elbv2", region_name="eu-central-1")
    with pytest.raises(ClientError) as exc:
        client.describe_listener_certificates(ListenerArn="unknown")
    err = exc.value.response["Error"]
    assert err["Code"] == "ListenerNotFound"


@mock_acm
@mock_ec2
@mock_elbv2
def test_add_listener_certificate():
    # Verify we can add a listener for a TargetGroup that is already HTTPS
    client = boto3.client("elbv2", region_name="eu-central-1")
    acm = boto3.client("acm", region_name="eu-central-1")
    ec2 = boto3.resource("ec2", region_name="eu-central-1")

    vpc = ec2.create_vpc(CidrBlock="172.28.7.0/24", InstanceTenancy="default")
    subnet1 = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="172.28.7.192/26", AvailabilityZone="eu-central-1a"
    )

    response = client.create_load_balancer(
        Name="my-lb",
        Subnets=[subnet1.id],
        Scheme="internal",
        Tags=[{"Key": "key_name", "Value": "a_value"}],
    )

    load_balancer_arn = response["LoadBalancers"][0]["LoadBalancerArn"]

    response = client.create_target_group(
        Name="a-target", Protocol="HTTPS", Port=8443, VpcId=vpc.id
    )
    target_group_arn = response["TargetGroups"][0]["TargetGroupArn"]

    # HTTPS listener
    response = acm.request_certificate(
        DomainName="google.com", SubjectAlternativeNames=["google.com"]
    )
    google_arn = response["CertificateArn"]
    response = client.create_listener(
        LoadBalancerArn=load_balancer_arn,
        Protocol="HTTPS",
        Port=443,
        DefaultActions=[{"Type": "forward", "TargetGroupArn": target_group_arn}],
    )
    listener_arn = response["Listeners"][0]["ListenerArn"]

    certs = client.add_listener_certificates(
        ListenerArn=listener_arn, Certificates=[{"CertificateArn": google_arn}]
    )["Certificates"]
    assert len(certs) == 1
    assert certs[0]["CertificateArn"] == google_arn

    certs = client.describe_listener_certificates(ListenerArn=listener_arn)[
        "Certificates"
    ]
    assert len(certs) == 1
    assert certs[0]["CertificateArn"] == google_arn

    client.remove_listener_certificates(
        ListenerArn=listener_arn, Certificates=[{"CertificateArn": google_arn}]
    )

    certs = client.describe_listener_certificates(ListenerArn=listener_arn)[
        "Certificates"
    ]
    assert len(certs) == 0


@mock_elbv2
@mock_ec2
def test_forward_config_action():
    response, vpc, _, _, _, conn = create_load_balancer()
    load_balancer_arn = response["LoadBalancers"][0]["LoadBalancerArn"]

    response = conn.create_target_group(
        Name="a-target", Protocol="HTTPS", Port=8443, VpcId=vpc.id
    )
    target_group_arn = response["TargetGroups"][0]["TargetGroupArn"]

    action = {
        "Type": "forward",
        "ForwardConfig": {
            "TargetGroups": [{"TargetGroupArn": target_group_arn, "Weight": 1}],
        },
    }
    expected_action = copy.deepcopy(action)
    expected_action["ForwardConfig"]["TargetGroupStickinessConfig"] = {"Enabled": False}

    response = conn.create_listener(
        LoadBalancerArn=load_balancer_arn,
        Protocol="HTTP",
        Port=80,
        DefaultActions=[action],
    )

    listener = response["Listeners"][0]
    assert listener["DefaultActions"] == [expected_action]
    listener_arn = listener["ListenerArn"]

    describe_listener_response = conn.describe_listeners(ListenerArns=[listener_arn])
    describe_listener_actions = describe_listener_response["Listeners"][0][
        "DefaultActions"
    ]
    assert describe_listener_actions == [expected_action]


@mock_elbv2
@mock_ec2
def test_forward_config_action__with_stickiness():
    response, vpc, _, _, _, conn = create_load_balancer()
    load_balancer_arn = response["LoadBalancers"][0]["LoadBalancerArn"]

    response = conn.create_target_group(
        Name="a-target", Protocol="HTTPS", Port=8443, VpcId=vpc.id
    )
    target_group_arn = response["TargetGroups"][0]["TargetGroupArn"]

    action = {
        "Type": "forward",
        "ForwardConfig": {
            "TargetGroups": [{"TargetGroupArn": target_group_arn, "Weight": 1}],
            "TargetGroupStickinessConfig": {"Enabled": True},
        },
    }

    response = conn.create_listener(
        LoadBalancerArn=load_balancer_arn,
        Protocol="HTTP",
        Port=80,
        DefaultActions=[action],
    )

    listener = response["Listeners"][0]
    assert listener["DefaultActions"] == [action]
    listener_arn = listener["ListenerArn"]

    describe_listener_response = conn.describe_listeners(ListenerArns=[listener_arn])
    describe_listener_actions = describe_listener_response["Listeners"][0][
        "DefaultActions"
    ]
    assert describe_listener_actions == [action]


@mock_elbv2
@mock_ec2
def test_redirect_action_listener_rule():
    response, _, _, _, _, conn = create_load_balancer()
    load_balancer_arn = response["LoadBalancers"][0]["LoadBalancerArn"]

    action = {
        "Type": "redirect",
        "RedirectConfig": {
            "Protocol": "HTTPS",
            "Port": "443",
            "StatusCode": "HTTP_301",
            "Host": "h",
            "Path": "p",
            "Query": "q",
        },
        "Order": 1,
    }

    response = conn.create_listener(
        LoadBalancerArn=load_balancer_arn,
        Protocol="HTTP",
        Port=80,
        DefaultActions=[action],
    )

    listener = response["Listeners"][0]
    assert listener["DefaultActions"] == [action]
    listener_arn = listener["ListenerArn"]

    conn.create_rule(
        ListenerArn=listener_arn,
        Conditions=[{"Field": "path-pattern", "Values": ["/*"]}],
        Priority=3,
        Actions=[action],
    )
    describe_rules_response = conn.describe_rules(ListenerArn=listener_arn)
    assert describe_rules_response["Rules"][0]["Actions"] == [action]

    describe_listener_response = conn.describe_listeners(ListenerArns=[listener_arn])
    describe_listener_actions = describe_listener_response["Listeners"][0][
        "DefaultActions"
    ]
    assert describe_listener_actions == [action]

    modify_listener_response = conn.modify_listener(ListenerArn=listener_arn, Port=81)
    modify_listener_actions = modify_listener_response["Listeners"][0]["DefaultActions"]
    assert modify_listener_actions == [action]


@mock_elbv2
@mock_ec2
def test_cognito_action_listener_rule():
    response, _, _, _, _, conn = create_load_balancer()
    load_balancer_arn = response["LoadBalancers"][0]["LoadBalancerArn"]

    action = {
        "Type": "authenticate-cognito",
        "AuthenticateCognitoConfig": {
            "UserPoolArn": f"arn:aws:cognito-idp:us-east-1:{ACCOUNT_ID}:userpool/us-east-1_ABCD1234",
            "UserPoolClientId": "abcd1234abcd",
            "UserPoolDomain": "testpool",
            "AuthenticationRequestExtraParams": {"param": "test"},
        },
    }
    response = conn.create_listener(
        LoadBalancerArn=load_balancer_arn,
        Protocol="HTTP",
        Port=80,
        DefaultActions=[action],
    )

    listener = response["Listeners"][0]
    assert listener["DefaultActions"][0] == action
    listener_arn = listener["ListenerArn"]

    conn.create_rule(
        ListenerArn=listener_arn,
        Conditions=[{"Field": "path-pattern", "Values": ["/*"]}],
        Priority=3,
        Actions=[action],
    )
    describe_rules_response = conn.describe_rules(ListenerArn=listener_arn)
    assert describe_rules_response["Rules"][0]["Actions"][0] == action

    describe_listener_response = conn.describe_listeners(ListenerArns=[listener_arn])
    describe_listener_actions = describe_listener_response["Listeners"][0][
        "DefaultActions"
    ][0]
    assert describe_listener_actions == action


@mock_elbv2
@mock_ec2
def test_oidc_action_listener__simple():
    response, _, _, _, _, conn = create_load_balancer()
    load_balancer_arn = response["LoadBalancers"][0]["LoadBalancerArn"]

    action = {
        "Type": "authenticate-oidc",
        "AuthenticateOidcConfig": {
            "AuthorizationEndpoint": "ae",
            "ClientId": "ci",
            "TokenEndpoint": "te",
            "UserInfoEndpoint": "uie",
            "Issuer": "is",
        },
    }
    response = conn.create_listener(
        LoadBalancerArn=load_balancer_arn,
        Protocol="HTTP",
        Port=80,
        DefaultActions=[action],
    )

    listener = response["Listeners"][0]
    assert listener["DefaultActions"][0] == action
    listener_arn = listener["ListenerArn"]

    conn.create_rule(
        ListenerArn=listener_arn,
        Conditions=[{"Field": "path-pattern", "Values": ["/*"]}],
        Priority=3,
        Actions=[action],
    )
    describe_rules_response = conn.describe_rules(ListenerArn=listener_arn)
    assert describe_rules_response["Rules"][0]["Actions"][0] == action

    describe_listener_response = conn.describe_listeners(ListenerArns=[listener_arn])
    describe_listener_actions = describe_listener_response["Listeners"][0][
        "DefaultActions"
    ][0]
    assert describe_listener_actions == action


@mock_elbv2
@mock_ec2
@pytest.mark.parametrize("use_secret", [True, False])
def test_oidc_action_listener(use_secret):
    response, _, _, _, _, conn = create_load_balancer()
    load_balancer_arn = response["LoadBalancers"][0]["LoadBalancerArn"]

    action = {
        "Type": "authenticate-oidc",
        "AuthenticateOidcConfig": {
            "Issuer": "is",
            "AuthorizationEndpoint": "ae",
            "TokenEndpoint": "te",
            "UserInfoEndpoint": "uie",
            "ClientId": "ci",
            "ClientSecret": "cs",
            "SessionCookieName": "scn",
            "Scope": "s",
            "SessionTimeout": 42,
            "AuthenticationRequestExtraParams": {"param": "test"},
            "OnUnauthenticatedRequest": "our",
            "UseExistingClientSecret": use_secret,
        },
    }
    response = conn.create_listener(
        LoadBalancerArn=load_balancer_arn,
        Protocol="HTTP",
        Port=80,
        DefaultActions=[action],
    )

    listener = response["Listeners"][0]
    assert listener["DefaultActions"][0] == action
    listener_arn = listener["ListenerArn"]

    conn.create_rule(
        ListenerArn=listener_arn,
        Conditions=[{"Field": "path-pattern", "Values": ["/*"]}],
        Priority=3,
        Actions=[action],
    )
    describe_rules_response = conn.describe_rules(ListenerArn=listener_arn)
    assert describe_rules_response["Rules"][0]["Actions"][0] == action

    describe_listener_response = conn.describe_listeners(ListenerArns=[listener_arn])
    describe_listener_actions = describe_listener_response["Listeners"][0][
        "DefaultActions"
    ][0]
    assert describe_listener_actions == action


@mock_elbv2
@mock_ec2
def test_fixed_response_action_listener_rule():
    response, _, _, _, _, conn = create_load_balancer()
    load_balancer_arn = response["LoadBalancers"][0]["LoadBalancerArn"]

    action = {
        "Type": "fixed-response",
        "FixedResponseConfig": {
            "ContentType": "text/plain",
            "MessageBody": "This page does not exist",
            "StatusCode": "404",
        },
    }
    response = conn.create_listener(
        LoadBalancerArn=load_balancer_arn,
        Protocol="HTTP",
        Port=80,
        DefaultActions=[action],
    )

    listener = response["Listeners"][0]
    assert listener["DefaultActions"][0] == action
    listener_arn = listener["ListenerArn"]

    conn.create_rule(
        ListenerArn=listener_arn,
        Conditions=[{"Field": "path-pattern", "Values": ["/*"]}],
        Priority=3,
        Actions=[action],
    )
    describe_rules_response = conn.describe_rules(ListenerArn=listener_arn)
    assert describe_rules_response["Rules"][0]["Actions"][0] == action

    describe_listener_response = conn.describe_listeners(ListenerArns=[listener_arn])
    describe_listener_actions = describe_listener_response["Listeners"][0][
        "DefaultActions"
    ][0]
    assert describe_listener_actions == action


@mock_elbv2
@mock_ec2
def test_fixed_response_action_listener_rule_validates_status_code():
    response, _, _, _, _, conn = create_load_balancer()
    load_balancer_arn = response["LoadBalancers"][0]["LoadBalancerArn"]

    invalid_status_code_action = {
        "Type": "fixed-response",
        "FixedResponseConfig": {
            "ContentType": "text/plain",
            "MessageBody": "This page does not exist",
            "StatusCode": "100",
        },
    }

    with pytest.raises(ClientError) as exc:
        conn.create_listener(
            LoadBalancerArn=load_balancer_arn,
            Protocol="HTTP",
            Port=80,
            DefaultActions=[invalid_status_code_action],
        )

    assert exc.value.response["Error"]["Code"] == "ValidationError"


@mock_elbv2
@mock_ec2
def test_fixed_response_action_listener_rule_validates_content_type():
    response, _, _, _, _, conn = create_load_balancer()
    load_balancer_arn = response["LoadBalancers"][0]["LoadBalancerArn"]

    invalid_content_type_action = {
        "Type": "fixed-response",
        "FixedResponseConfig": {
            "ContentType": "Fake content type",
            "MessageBody": "This page does not exist",
            "StatusCode": "200",
        },
    }
    with pytest.raises(ClientError) as exc:
        conn.create_listener(
            LoadBalancerArn=load_balancer_arn,
            Protocol="HTTP",
            Port=80,
            DefaultActions=[invalid_content_type_action],
        )
    assert exc.value.response["Error"]["Code"] == "InvalidLoadBalancerAction"


@mock_elbv2
@mock_ec2
def test_create_listener_with_alpn_policy():
    response, _, _, _, _, conn = create_load_balancer()
    load_balancer_arn = response["LoadBalancers"][0]["LoadBalancerArn"]

    response = conn.create_listener(
        LoadBalancerArn=load_balancer_arn,
        Protocol="HTTP",
        Port=80,
        DefaultActions=[],
        AlpnPolicy=["pol1", "pol2"],
    )

    listener = response["Listeners"][0]
    listener_arn = listener["ListenerArn"]
    assert listener["AlpnPolicy"] == ["pol1", "pol2"]

    describe = conn.describe_listeners(ListenerArns=[listener_arn])["Listeners"][0]
    assert describe["AlpnPolicy"] == ["pol1", "pol2"]
