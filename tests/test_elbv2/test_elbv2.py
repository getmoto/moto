from __future__ import unicode_literals

import os
import boto3
import botocore
from botocore.exceptions import ClientError
import pytest
import sure  # noqa

from moto import mock_elbv2, mock_ec2, mock_acm
from moto.elbv2 import elbv2_backends
from moto.core import ACCOUNT_ID
from tests import EXAMPLE_AMI_ID


@mock_elbv2
@mock_ec2
def test_create_load_balancer():
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

    lb = response.get("LoadBalancers")[0]

    lb.get("DNSName").should.equal("my-lb-1.us-east-1.elb.amazonaws.com")
    lb.get("LoadBalancerArn").should.equal(
        "arn:aws:elasticloadbalancing:us-east-1:1:loadbalancer/my-lb/50dc6c495c0c9188"
    )
    lb.get("SecurityGroups").should.equal([security_group.id])
    lb.get("AvailabilityZones").should.equal(
        [
            {"SubnetId": subnet1.id, "ZoneName": "us-east-1a"},
            {"SubnetId": subnet2.id, "ZoneName": "us-east-1b"},
        ]
    )
    lb.get("CreatedTime").tzinfo.should_not.be.none
    lb.get("State").get("Code").should.equal("provisioning")

    # Ensure the tags persisted
    response = conn.describe_tags(ResourceArns=[lb.get("LoadBalancerArn")])
    tags = {d["Key"]: d["Value"] for d in response["TagDescriptions"][0]["Tags"]}
    tags.should.equal({"key_name": "a_value"})


@mock_elbv2
@mock_ec2
def test_describe_load_balancers():
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

    response = conn.describe_load_balancers()

    response.get("LoadBalancers").should.have.length_of(1)
    lb = response.get("LoadBalancers")[0]
    lb.get("LoadBalancerName").should.equal("my-lb")
    lb.get("State").get("Code").should.equal("active")

    response = conn.describe_load_balancers(
        LoadBalancerArns=[lb.get("LoadBalancerArn")]
    )
    response.get("LoadBalancers")[0].get("LoadBalancerName").should.equal("my-lb")

    response = conn.describe_load_balancers(Names=["my-lb"])
    response.get("LoadBalancers")[0].get("LoadBalancerName").should.equal("my-lb")

    with pytest.raises(ClientError):
        conn.describe_load_balancers(LoadBalancerArns=["not-a/real/arn"])
    with pytest.raises(ClientError):
        conn.describe_load_balancers(Names=["nope"])


@mock_elbv2
@mock_ec2
def test_add_remove_tags():
    conn = boto3.client("elbv2", region_name="us-east-1")

    ec2 = boto3.resource("ec2", region_name="us-east-1")

    security_group = ec2.create_security_group(
        GroupName="a-security-group", Description="First One"
    )
    vpc = ec2.create_vpc(CidrBlock="172.28.7.0/24", InstanceTenancy="default")
    subnet1 = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="172.28.7.0/26", AvailabilityZone="us-east-1a"
    )
    subnet2 = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="172.28.7.192/26", AvailabilityZone="us-east-1b"
    )

    conn.create_load_balancer(
        Name="my-lb",
        Subnets=[subnet1.id, subnet2.id],
        SecurityGroups=[security_group.id],
        Scheme="internal",
        Tags=[{"Key": "key_name", "Value": "a_value"}],
    )

    lbs = conn.describe_load_balancers()["LoadBalancers"]
    lbs.should.have.length_of(1)
    lb = lbs[0]

    with pytest.raises(ClientError):
        conn.add_tags(ResourceArns=["missing-arn"], Tags=[{"Key": "a", "Value": "b"}])

    conn.add_tags(
        ResourceArns=[lb.get("LoadBalancerArn")], Tags=[{"Key": "a", "Value": "b"}]
    )

    tags = {
        d["Key"]: d["Value"]
        for d in conn.describe_tags(ResourceArns=[lb.get("LoadBalancerArn")])[
            "TagDescriptions"
        ][0]["Tags"]
    }
    tags.should.have.key("a").which.should.equal("b")

    conn.add_tags(
        ResourceArns=[lb.get("LoadBalancerArn")],
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

    conn.add_tags.when.called_with(
        ResourceArns=[lb.get("LoadBalancerArn")], Tags=[{"Key": "k", "Value": "b"}]
    ).should.throw(botocore.exceptions.ClientError)

    conn.add_tags(
        ResourceArns=[lb.get("LoadBalancerArn")], Tags=[{"Key": "j", "Value": "c"}]
    )

    tags = {
        d["Key"]: d["Value"]
        for d in conn.describe_tags(ResourceArns=[lb.get("LoadBalancerArn")])[
            "TagDescriptions"
        ][0]["Tags"]
    }

    tags.should.have.key("a").which.should.equal("b")
    tags.should.have.key("b").which.should.equal("b")
    tags.should.have.key("c").which.should.equal("b")
    tags.should.have.key("d").which.should.equal("b")
    tags.should.have.key("e").which.should.equal("b")
    tags.should.have.key("f").which.should.equal("b")
    tags.should.have.key("g").which.should.equal("b")
    tags.should.have.key("h").which.should.equal("b")
    tags.should.have.key("j").which.should.equal("c")
    tags.shouldnt.have.key("k")

    conn.remove_tags(ResourceArns=[lb.get("LoadBalancerArn")], TagKeys=["a"])

    tags = {
        d["Key"]: d["Value"]
        for d in conn.describe_tags(ResourceArns=[lb.get("LoadBalancerArn")])[
            "TagDescriptions"
        ][0]["Tags"]
    }

    tags.shouldnt.have.key("a")
    tags.should.have.key("b").which.should.equal("b")
    tags.should.have.key("c").which.should.equal("b")
    tags.should.have.key("d").which.should.equal("b")
    tags.should.have.key("e").which.should.equal("b")
    tags.should.have.key("f").which.should.equal("b")
    tags.should.have.key("g").which.should.equal("b")
    tags.should.have.key("h").which.should.equal("b")
    tags.should.have.key("j").which.should.equal("c")


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

    list(
        boto3.client("elbv2", region_name="us-west-1")
        .describe_load_balancers()
        .get("LoadBalancers")
    ).should.have.length_of(1)
    list(
        boto3.client("elbv2", region_name="us-west-2")
        .describe_load_balancers()
        .get("LoadBalancers")
    ).should.have.length_of(1)


@mock_elbv2
@mock_ec2
def test_create_target_group_and_listeners():
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

    load_balancer_arn = response.get("LoadBalancers")[0].get("LoadBalancerArn")

    # Can't create a target group with an invalid protocol
    with pytest.raises(ClientError):
        conn.create_target_group(
            Name="a-target",
            Protocol="HTTP",
            Port=8080,
            VpcId=vpc.id,
            HealthCheckProtocol="/HTTP",
            HealthCheckPort="8080",
            HealthCheckPath="/",
            HealthCheckIntervalSeconds=5,
            HealthCheckTimeoutSeconds=5,
            HealthyThresholdCount=5,
            UnhealthyThresholdCount=2,
            Matcher={"HttpCode": "200"},
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
        HealthCheckTimeoutSeconds=5,
        HealthyThresholdCount=5,
        UnhealthyThresholdCount=2,
        Matcher={"HttpCode": "200"},
    )
    target_group = response.get("TargetGroups")[0]
    target_group_arn = target_group["TargetGroupArn"]

    # Add tags to the target group
    conn.add_tags(
        ResourceArns=[target_group_arn], Tags=[{"Key": "target", "Value": "group"}]
    )
    conn.describe_tags(ResourceArns=[target_group_arn])["TagDescriptions"][0][
        "Tags"
    ].should.equal([{"Key": "target", "Value": "group"}])

    # Check it's in the describe_target_groups response
    response = conn.describe_target_groups()
    response.get("TargetGroups").should.have.length_of(1)

    # Plain HTTP listener
    response = conn.create_listener(
        LoadBalancerArn=load_balancer_arn,
        Protocol="HTTP",
        Port=80,
        DefaultActions=[
            {"Type": "forward", "TargetGroupArn": target_group.get("TargetGroupArn")}
        ],
    )
    listener = response.get("Listeners")[0]
    listener.get("Port").should.equal(80)
    listener.get("Protocol").should.equal("HTTP")
    listener.get("DefaultActions").should.equal(
        [{"TargetGroupArn": target_group.get("TargetGroupArn"), "Type": "forward"}]
    )
    http_listener_arn = listener.get("ListenerArn")

    response = conn.describe_target_groups(
        LoadBalancerArn=load_balancer_arn, Names=["a-target"]
    )
    response.get("TargetGroups").should.have.length_of(1)

    # And another with SSL
    actions = {"Type": "forward", "TargetGroupArn": target_group.get("TargetGroupArn")}
    response = conn.create_listener(
        LoadBalancerArn=load_balancer_arn,
        Protocol="HTTPS",
        Port=443,
        Certificates=[
            {
                "CertificateArn": "arn:aws:iam:{}:server-certificate/test-cert".format(
                    ACCOUNT_ID
                )
            }
        ],
        DefaultActions=[actions],
    )
    listener = response.get("Listeners")[0]
    listener.get("Port").should.equal(443)
    listener.get("Protocol").should.equal("HTTPS")
    listener.get("Certificates").should.equal(
        [
            {
                "CertificateArn": "arn:aws:iam:{}:server-certificate/test-cert".format(
                    ACCOUNT_ID
                )
            }
        ]
    )
    listener.get("DefaultActions").should.equal(
        [{"TargetGroupArn": target_group.get("TargetGroupArn"), "Type": "forward"}]
    )

    https_listener_arn = listener.get("ListenerArn")

    response = conn.describe_listeners(LoadBalancerArn=load_balancer_arn)
    response.get("Listeners").should.have.length_of(2)
    response = conn.describe_listeners(ListenerArns=[https_listener_arn])
    response.get("Listeners").should.have.length_of(1)
    listener = response.get("Listeners")[0]
    listener.get("Port").should.equal(443)
    listener.get("Protocol").should.equal("HTTPS")

    response = conn.describe_listeners(
        ListenerArns=[http_listener_arn, https_listener_arn]
    )
    response.get("Listeners").should.have.length_of(2)

    listener_response = conn.create_rule(
        ListenerArn=http_listener_arn,
        Conditions=[{"Field": "path-pattern", "Values": ["/*"]},],
        Priority=3,
        Actions=[actions],
    )
    # Try to delete the target group and it fails because there's a
    # listener referencing it
    with pytest.raises(ClientError) as e:
        conn.delete_target_group(TargetGroupArn=target_group.get("TargetGroupArn"))
    e.value.operation_name.should.equal("DeleteTargetGroup")
    e.value.args.should.equal(
        (
            "An error occurred (ResourceInUse) when calling the DeleteTargetGroup operation: The target group 'arn:aws:elasticloadbalancing:us-east-1:1:targetgroup/a-target/50dc6c495c0c9188' is currently in use by a listener or a rule",
        )
    )  # NOQA

    # Delete one listener
    response = conn.describe_listeners(LoadBalancerArn=load_balancer_arn)
    response.get("Listeners").should.have.length_of(2)
    conn.delete_listener(ListenerArn=http_listener_arn)
    response = conn.describe_listeners(LoadBalancerArn=load_balancer_arn)
    response.get("Listeners").should.have.length_of(1)

    # Then delete the load balancer
    conn.delete_load_balancer(LoadBalancerArn=load_balancer_arn)

    # It's gone
    response = conn.describe_load_balancers()
    response.get("LoadBalancers").should.have.length_of(0)

    # And it deleted the remaining listener
    with pytest.raises(ClientError) as e:
        conn.describe_listeners(ListenerArns=[http_listener_arn, https_listener_arn])
    e.value.response["Error"]["Code"].should.equal("ListenerNotFound")

    # But not the target groups
    response = conn.describe_target_groups()
    response.get("TargetGroups").should.have.length_of(1)

    # Which we'll now delete
    conn.delete_target_group(TargetGroupArn=target_group.get("TargetGroupArn"))
    response = conn.describe_target_groups()
    response.get("TargetGroups").should.have.length_of(0)


@mock_elbv2
@mock_ec2
def test_create_target_group_without_non_required_parameters():
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

    # request without HealthCheckIntervalSeconds parameter
    # which is default to 30 seconds
    response = conn.create_target_group(
        Name="a-target",
        Protocol="HTTP",
        Port=8080,
        VpcId=vpc.id,
        HealthCheckProtocol="HTTP",
        HealthCheckPort="8080",
    )
    target_group = response.get("TargetGroups")[0]
    target_group.should_not.be.none


@mock_elbv2
@mock_ec2
def test_create_invalid_target_group():
    conn = boto3.client("elbv2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    vpc = ec2.create_vpc(CidrBlock="172.28.7.0/24", InstanceTenancy="default")

    # Fail to create target group with name which length is 33
    long_name = "A" * 33
    with pytest.raises(ClientError):
        conn.create_target_group(
            Name=long_name,
            Protocol="HTTP",
            Port=8080,
            VpcId=vpc.id,
            HealthCheckProtocol="HTTP",
            HealthCheckPort="8080",
            HealthCheckPath="/",
            HealthCheckIntervalSeconds=5,
            HealthCheckTimeoutSeconds=5,
            HealthyThresholdCount=5,
            UnhealthyThresholdCount=2,
            Matcher={"HttpCode": "200"},
        )

    invalid_names = ["-name", "name-", "-name-", "example.com", "test@test", "Na--me"]
    for name in invalid_names:
        with pytest.raises(ClientError):
            conn.create_target_group(
                Name=name,
                Protocol="HTTP",
                Port=8080,
                VpcId=vpc.id,
                HealthCheckProtocol="HTTP",
                HealthCheckPort="8080",
                HealthCheckPath="/",
                HealthCheckIntervalSeconds=5,
                HealthCheckTimeoutSeconds=5,
                HealthyThresholdCount=5,
                UnhealthyThresholdCount=2,
                Matcher={"HttpCode": "200"},
            )

    valid_names = ["name", "Name", "000"]
    for name in valid_names:
        conn.create_target_group(
            Name=name,
            Protocol="HTTP",
            Port=8080,
            VpcId=vpc.id,
            HealthCheckProtocol="HTTP",
            HealthCheckPort="8080",
            HealthCheckPath="/",
            HealthCheckIntervalSeconds=5,
            HealthCheckTimeoutSeconds=5,
            HealthyThresholdCount=5,
            UnhealthyThresholdCount=2,
            Matcher={"HttpCode": "200"},
        )


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
            Name="my-lb%d" % i,
            Subnets=[subnet1.id, subnet2.id],
            SecurityGroups=[security_group.id],
            Scheme="internal",
            Tags=[{"Key": "key_name", "Value": "a_value"}],
        )

    resp = conn.describe_load_balancers()
    resp["LoadBalancers"].should.have.length_of(50)
    resp["NextMarker"].should.equal(resp["LoadBalancers"][-1]["LoadBalancerName"])
    resp2 = conn.describe_load_balancers(Marker=resp["NextMarker"])
    resp2["LoadBalancers"].should.have.length_of(1)
    assert "NextToken" not in resp2.keys()


@mock_elbv2
@mock_ec2
def test_delete_load_balancer():
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

    response.get("LoadBalancers").should.have.length_of(1)
    lb = response.get("LoadBalancers")[0]

    conn.delete_load_balancer(LoadBalancerArn=lb.get("LoadBalancerArn"))
    balancers = conn.describe_load_balancers().get("LoadBalancers")
    balancers.should.have.length_of(0)


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
        HealthCheckTimeoutSeconds=5,
        HealthyThresholdCount=5,
        UnhealthyThresholdCount=2,
        Matcher={"HttpCode": "200"},
    )
    target_group = response.get("TargetGroups")[0]

    # No targets registered yet
    response = conn.describe_target_health(
        TargetGroupArn=target_group.get("TargetGroupArn")
    )
    response.get("TargetHealthDescriptions").should.have.length_of(0)

    response = ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=2, MaxCount=2)
    instance_id1 = response[0].id
    instance_id2 = response[1].id

    response = conn.register_targets(
        TargetGroupArn=target_group.get("TargetGroupArn"),
        Targets=[
            {"Id": instance_id1, "Port": 5060},
            {"Id": instance_id2, "Port": 4030},
        ],
    )

    response = conn.describe_target_health(
        TargetGroupArn=target_group.get("TargetGroupArn")
    )
    response.get("TargetHealthDescriptions").should.have.length_of(2)

    response = conn.deregister_targets(
        TargetGroupArn=target_group.get("TargetGroupArn"),
        Targets=[{"Id": instance_id2}],
    )

    response = conn.describe_target_health(
        TargetGroupArn=target_group.get("TargetGroupArn")
    )
    response.get("TargetHealthDescriptions").should.have.length_of(1)


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
        HealthCheckTimeoutSeconds=5,
        HealthyThresholdCount=5,
        UnhealthyThresholdCount=2,
        Matcher={"HttpCode": "200"},
    )
    target_group = response.get("TargetGroups")[0]

    # No targets registered yet
    response = conn.describe_target_health(
        TargetGroupArn=target_group.get("TargetGroupArn")
    )
    response.get("TargetHealthDescriptions").should.have.length_of(0)

    response = ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    instance = response[0]

    target_dict = {"Id": instance.id, "Port": 500}

    response = conn.register_targets(
        TargetGroupArn=target_group.get("TargetGroupArn"), Targets=[target_dict]
    )

    response = conn.describe_target_health(
        TargetGroupArn=target_group.get("TargetGroupArn")
    )
    response.get("TargetHealthDescriptions").should.have.length_of(1)
    target_health_description = response.get("TargetHealthDescriptions")[0]

    target_health_description["Target"].should.equal(target_dict)
    target_health_description["HealthCheckPort"].should.equal(str(target_group_port))
    target_health_description["TargetHealth"].should.equal({"State": "healthy"})

    instance.stop()

    response = conn.describe_target_health(
        TargetGroupArn=target_group.get("TargetGroupArn")
    )
    response.get("TargetHealthDescriptions").should.have.length_of(1)
    target_health_description = response.get("TargetHealthDescriptions")[0]
    target_health_description["Target"].should.equal(target_dict)
    target_health_description["HealthCheckPort"].should.equal(str(target_group_port))
    target_health_description["TargetHealth"].should.equal(
        {
            "State": "unused",
            "Reason": "Target.InvalidState",
            "Description": "Target is in the stopped state",
        }
    )


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
        HealthCheckTimeoutSeconds=5,
        HealthyThresholdCount=5,
        UnhealthyThresholdCount=2,
        Matcher={"HttpCode": "200"},
    )
    target_group = response.get("TargetGroups")[0]

    # No targets registered yet
    response = conn.describe_target_health(
        TargetGroupArn=target_group.get("TargetGroupArn")
    )
    response.get("TargetHealthDescriptions").should.have.length_of(0)

    response = ec2.create_instances(ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1)
    instance = response[0]

    target_dict = {"Id": instance.id, "Port": 500}

    response = conn.register_targets(
        TargetGroupArn=target_group.get("TargetGroupArn"), Targets=[target_dict]
    )

    response = conn.describe_target_health(
        TargetGroupArn=target_group.get("TargetGroupArn")
    )
    response.get("TargetHealthDescriptions").should.have.length_of(1)
    target_health_description = response.get("TargetHealthDescriptions")[0]

    target_health_description["Target"].should.equal(target_dict)
    target_health_description["HealthCheckPort"].should.equal(str(target_group_port))
    target_health_description["TargetHealth"].should.equal({"State": "healthy"})

    instance.terminate()

    response = conn.describe_target_health(
        TargetGroupArn=target_group.get("TargetGroupArn")
    )
    response.get("TargetHealthDescriptions").should.have.length_of(0)


@mock_ec2
@mock_elbv2
def test_target_group_attributes():
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

    response = conn.create_target_group(
        Name="a-target",
        Protocol="HTTP",
        Port=8080,
        VpcId=vpc.id,
        HealthCheckProtocol="HTTP",
        HealthCheckPort="8080",
        HealthCheckPath="/",
        HealthCheckIntervalSeconds=5,
        HealthCheckTimeoutSeconds=5,
        HealthyThresholdCount=5,
        UnhealthyThresholdCount=2,
        Matcher={"HttpCode": "200"},
    )
    target_group = response.get("TargetGroups")[0]

    # Check it's in the describe_target_groups response
    response = conn.describe_target_groups()
    response.get("TargetGroups").should.have.length_of(1)
    target_group_arn = target_group["TargetGroupArn"]

    # check if Names filter works
    response = conn.describe_target_groups(Names=[])
    response = conn.describe_target_groups(Names=["a-target"])
    response.get("TargetGroups").should.have.length_of(1)
    target_group_arn = target_group["TargetGroupArn"]

    # The attributes should start with the two defaults
    response = conn.describe_target_group_attributes(TargetGroupArn=target_group_arn)
    response["Attributes"].should.have.length_of(2)
    attributes = {attr["Key"]: attr["Value"] for attr in response["Attributes"]}
    attributes["deregistration_delay.timeout_seconds"].should.equal("300")
    attributes["stickiness.enabled"].should.equal("false")

    # Add cookie stickiness
    response = conn.modify_target_group_attributes(
        TargetGroupArn=target_group_arn,
        Attributes=[
            {"Key": "stickiness.enabled", "Value": "true"},
            {"Key": "stickiness.type", "Value": "lb_cookie"},
        ],
    )

    # The response should have only the keys updated
    response["Attributes"].should.have.length_of(2)
    attributes = {attr["Key"]: attr["Value"] for attr in response["Attributes"]}
    attributes["stickiness.type"].should.equal("lb_cookie")
    attributes["stickiness.enabled"].should.equal("true")

    # These new values should be in the full attribute list
    response = conn.describe_target_group_attributes(TargetGroupArn=target_group_arn)
    response["Attributes"].should.have.length_of(3)
    attributes = {attr["Key"]: attr["Value"] for attr in response["Attributes"]}
    attributes["stickiness.type"].should.equal("lb_cookie")
    attributes["stickiness.enabled"].should.equal("true")


@mock_elbv2
@mock_ec2
def test_create_target_group_invalid_protocol():
    elbv2 = boto3.client("elbv2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    vpc = ec2.create_vpc(CidrBlock="172.28.7.0/24", InstanceTenancy="default")

    # Can't create a target group with an invalid protocol
    with pytest.raises(ClientError) as ex:
        elbv2.create_target_group(
            Name="a-target",
            Protocol="HTTP",
            Port=8080,
            VpcId=vpc.id,
            HealthCheckProtocol="/HTTP",
            HealthCheckPort="8080",
            HealthCheckPath="/",
            HealthCheckIntervalSeconds=5,
            HealthCheckTimeoutSeconds=5,
            HealthyThresholdCount=5,
            UnhealthyThresholdCount=2,
            Matcher={"HttpCode": "200"},
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("ValidationError")
    err["Message"].should.contain(
        "Value /HTTP at 'healthCheckProtocol' failed to satisfy constraint"
    )


@mock_elbv2
@mock_ec2
def test_create_rule_priority_in_use():
    elbv2 = boto3.client("elbv2", region_name="us-east-1")
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

    response = elbv2.create_load_balancer(
        Name="my-lb",
        Subnets=[subnet1.id, subnet2.id],
        SecurityGroups=[security_group.id],
        Scheme="internal",
        Tags=[{"Key": "key_name", "Value": "a_value"}],
    )

    load_balancer_arn = response.get("LoadBalancers")[0].get("LoadBalancerArn")

    response = elbv2.create_listener(
        LoadBalancerArn=load_balancer_arn, Protocol="HTTP", Port=80, DefaultActions=[],
    )
    http_listener_arn = response.get("Listeners")[0]["ListenerArn"]

    priority = 100
    elbv2.create_rule(
        ListenerArn=http_listener_arn, Priority=priority, Conditions=[], Actions=[],
    )

    # test for PriorityInUse
    with pytest.raises(ClientError) as ex:
        elbv2.create_rule(
            ListenerArn=http_listener_arn, Priority=priority, Conditions=[], Actions=[],
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("PriorityInUse")
    err["Message"].should.equal("The specified priority is in use.")


@mock_elbv2
@mock_ec2
def test_handle_listener_rules():
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

    load_balancer_arn = response.get("LoadBalancers")[0].get("LoadBalancerArn")

    response = conn.create_target_group(
        Name="a-target",
        Protocol="HTTP",
        Port=8080,
        VpcId=vpc.id,
        HealthCheckProtocol="HTTP",
        HealthCheckPort="8080",
        HealthCheckPath="/",
        HealthCheckIntervalSeconds=5,
        HealthCheckTimeoutSeconds=5,
        HealthyThresholdCount=5,
        UnhealthyThresholdCount=2,
        Matcher={"HttpCode": "200"},
    )
    target_group = response.get("TargetGroups")[0]

    # Plain HTTP listener
    response = conn.create_listener(
        LoadBalancerArn=load_balancer_arn,
        Protocol="HTTP",
        Port=80,
        DefaultActions=[
            {"Type": "forward", "TargetGroupArn": target_group.get("TargetGroupArn")}
        ],
    )
    listener = response.get("Listeners")[0]
    listener.get("Port").should.equal(80)
    listener.get("Protocol").should.equal("HTTP")
    listener.get("DefaultActions").should.equal(
        [{"TargetGroupArn": target_group.get("TargetGroupArn"), "Type": "forward"}]
    )
    http_listener_arn = listener.get("ListenerArn")

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
        Actions=[
            {"TargetGroupArn": target_group.get("TargetGroupArn"), "Type": "forward"}
        ],
    )
    rule = created_rule.get("Rules")[0]
    rule["Priority"].should.equal("100")

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
        Actions=[
            {"TargetGroupArn": target_group.get("TargetGroupArn"), "Type": "forward"}
        ],
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
                            "TargetGroupArn": target_group.get("TargetGroupArn"),
                            "Weight": 1,
                        },
                        {
                            "TargetGroupArn": target_group.get("TargetGroupArn"),
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
                    "TargetGroupArn": target_group.get("TargetGroupArn"),
                    "Type": "forward",
                }
            ],
        )

    # test for describe listeners
    obtained_rules = conn.describe_rules(ListenerArn=http_listener_arn)
    obtained_rules["Rules"].should.have.length_of(4)
    priorities = [rule["Priority"] for rule in obtained_rules["Rules"]]
    priorities.should.equal(["100", "500", "550", "default"])

    first_rule = obtained_rules["Rules"][0]
    second_rule = obtained_rules["Rules"][1]
    third_rule = obtained_rules["Rules"][2]
    obtained_rules = conn.describe_rules(RuleArns=[first_rule["RuleArn"]])
    obtained_rules["Rules"].should.equal([first_rule])

    # test for pagination
    obtained_rules = conn.describe_rules(ListenerArn=http_listener_arn, PageSize=1)
    len(obtained_rules["Rules"]).should.equal(1)
    obtained_rules.should.have.key("NextMarker")
    next_marker = obtained_rules["NextMarker"]

    following_rules = conn.describe_rules(
        ListenerArn=http_listener_arn, PageSize=1, Marker=next_marker
    )
    len(following_rules["Rules"]).should.equal(1)
    following_rules["Rules"][0]["RuleArn"].should_not.equal(
        obtained_rules["Rules"][0]["RuleArn"]
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
    modified_rule = conn.modify_rule(
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
    obtained_rule["Conditions"][0]["Values"][0].should.equal(new_host)
    obtained_rule["Conditions"][1]["Values"][0].should.equal(new_path_pattern)
    obtained_rule["Conditions"][2]["Values"][0].should.equal(
        new_pathpatternconfig_pattern
    )
    obtained_rule["Actions"][0]["TargetGroupArn"].should.equal(
        target_group.get("TargetGroupArn")
    )

    # modify priority
    conn.set_rule_priorities(
        RulePriorities=[
            {
                "RuleArn": first_rule["RuleArn"],
                "Priority": int(first_rule["Priority"]) - 1,
            }
        ]
    )

    # modify forward_config rule partially rule
    new_host_2 = "new.examplewebsite.com"
    new_path_pattern_2 = "new_path_2"
    new_pathpatternconfig_pattern_2 = "new_path_2"
    modified_rule = conn.modify_rule(
        RuleArn=third_rule["RuleArn"],
        Conditions=[
            {"Field": "host-header", "Values": [new_host_2]},
            {"Field": "path-pattern", "Values": [new_path_pattern_2]},
            {
                "Field": "path-pattern",
                "PathPatternConfig": {"Values": [new_pathpatternconfig_pattern_2]},
            },
        ],
        Actions=[
            {"TargetGroupArn": target_group.get("TargetGroupArn"), "Type": "forward",}
        ],
    )

    rules = conn.describe_rules(ListenerArn=http_listener_arn)
    obtained_rule = rules["Rules"][2]
    obtained_rule["Conditions"][0]["Values"][0].should.equal(new_host_2)
    obtained_rule["Conditions"][1]["Values"][0].should.equal(new_path_pattern_2)
    obtained_rule["Conditions"][2]["Values"][0].should.equal(
        new_pathpatternconfig_pattern_2
    )
    obtained_rule["Actions"][0]["TargetGroupArn"].should.equal(
        target_group.get("TargetGroupArn")
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
    len(rules).should.equal(3)

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
                    "TargetGroupArn": target_group.get("TargetGroupArn"),
                    "Type": "forward2",
                }
            ],
        )

    # test for invalid action type
    safe_priority = 2
    invalid_target_group_arn = target_group.get("TargetGroupArn") + "x"
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
                    "TargetGroupArn": target_group.get("TargetGroupArn"),
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
                    "TargetGroupArn": target_group.get("TargetGroupArn"),
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
                    "TargetGroupArn": target_group.get("TargetGroupArn"),
                    "Type": "forward",
                }
            ],
        )


@mock_elbv2
@mock_ec2
def test_describe_invalid_target_group():
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

    response.get("LoadBalancers")[0].get("LoadBalancerArn")

    response = conn.create_target_group(
        Name="a-target",
        Protocol="HTTP",
        Port=8080,
        VpcId=vpc.id,
        HealthCheckProtocol="HTTP",
        HealthCheckPort="8080",
        HealthCheckPath="/",
        HealthCheckIntervalSeconds=5,
        HealthCheckTimeoutSeconds=5,
        HealthyThresholdCount=5,
        UnhealthyThresholdCount=2,
        Matcher={"HttpCode": "200"},
    )

    # Check error raises correctly
    with pytest.raises(ClientError):
        conn.describe_target_groups(Names=["invalid"])


@mock_elbv2
@mock_ec2
def test_describe_target_groups_no_arguments():
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

    response.get("LoadBalancers")[0].get("LoadBalancerArn")

    conn.create_target_group(
        Name="a-target",
        Protocol="HTTP",
        Port=8080,
        VpcId=vpc.id,
        HealthCheckProtocol="HTTP",
        HealthCheckPort="8080",
        HealthCheckPath="/",
        HealthCheckIntervalSeconds=5,
        HealthCheckTimeoutSeconds=5,
        HealthyThresholdCount=5,
        UnhealthyThresholdCount=2,
        Matcher={"HttpCode": "200"},
    )

    assert len(conn.describe_target_groups()["TargetGroups"]) == 1


@mock_elbv2
def test_describe_account_limits():
    client = boto3.client("elbv2", region_name="eu-central-1")

    resp = client.describe_account_limits()
    resp["Limits"][0].should.contain("Name")
    resp["Limits"][0].should.contain("Max")


@mock_elbv2
def test_describe_ssl_policies():
    client = boto3.client("elbv2", region_name="eu-central-1")

    resp = client.describe_ssl_policies()
    len(resp["SslPolicies"]).should.equal(5)

    resp = client.describe_ssl_policies(
        Names=["ELBSecurityPolicy-TLS-1-2-2017-01", "ELBSecurityPolicy-2016-08"]
    )
    len(resp["SslPolicies"]).should.equal(2)


@mock_elbv2
@mock_ec2
def test_set_ip_address_type():
    client = boto3.client("elbv2", region_name="us-east-1")
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

    response = client.create_load_balancer(
        Name="my-lb",
        Subnets=[subnet1.id, subnet2.id],
        SecurityGroups=[security_group.id],
        Scheme="internal",
        Tags=[{"Key": "key_name", "Value": "a_value"}],
    )
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
    len(resp["LoadBalancers"][0]["SecurityGroups"]).should.equal(2)

    with pytest.raises(ClientError):
        client.set_security_groups(LoadBalancerArn=arn, SecurityGroups=["non_existent"])


@mock_elbv2
@mock_ec2
def test_set_subnets():
    client = boto3.client("elbv2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    security_group = ec2.create_security_group(
        GroupName="a-security-group", Description="First One"
    )
    vpc = ec2.create_vpc(CidrBlock="172.28.7.0/24", InstanceTenancy="default")
    subnet1 = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="172.28.7.0/26", AvailabilityZone="us-east-1a"
    )
    subnet2 = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="172.28.7.64/26", AvailabilityZone="us-east-1b"
    )
    subnet3 = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="172.28.7.192/26", AvailabilityZone="us-east-1c"
    )

    response = client.create_load_balancer(
        Name="my-lb",
        Subnets=[subnet1.id, subnet2.id],
        SecurityGroups=[security_group.id],
        Scheme="internal",
        Tags=[{"Key": "key_name", "Value": "a_value"}],
    )
    arn = response["LoadBalancers"][0]["LoadBalancerArn"]

    client.set_subnets(
        LoadBalancerArn=arn, Subnets=[subnet1.id, subnet2.id, subnet3.id]
    )

    resp = client.describe_load_balancers(LoadBalancerArns=[arn])
    len(resp["LoadBalancers"][0]["AvailabilityZones"]).should.equal(3)

    # Only 1 AZ
    with pytest.raises(ClientError):
        client.set_subnets(LoadBalancerArn=arn, Subnets=[subnet1.id])

    # Multiple subnets in same AZ
    with pytest.raises(ClientError):
        client.set_subnets(
            LoadBalancerArn=arn, Subnets=[subnet1.id, subnet2.id, subnet2.id]
        )


@mock_elbv2
@mock_ec2
def test_set_subnets():
    client = boto3.client("elbv2", region_name="us-east-1")
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

    response = client.create_load_balancer(
        Name="my-lb",
        Subnets=[subnet1.id, subnet2.id],
        SecurityGroups=[security_group.id],
        Scheme="internal",
        Tags=[{"Key": "key_name", "Value": "a_value"}],
    )
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
    idle_timeout["Value"].should.equal("600")


@mock_elbv2
@mock_ec2
def test_modify_target_group():
    client = boto3.client("elbv2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    vpc = ec2.create_vpc(CidrBlock="172.28.7.0/24", InstanceTenancy="default")

    response = client.create_target_group(
        Name="a-target",
        Protocol="HTTP",
        Port=8080,
        VpcId=vpc.id,
        HealthCheckProtocol="HTTP",
        HealthCheckPort="8080",
        HealthCheckPath="/",
        HealthCheckIntervalSeconds=5,
        HealthCheckTimeoutSeconds=5,
        HealthyThresholdCount=5,
        UnhealthyThresholdCount=2,
        Matcher={"HttpCode": "200"},
    )
    arn = response.get("TargetGroups")[0]["TargetGroupArn"]

    client.modify_target_group(
        TargetGroupArn=arn,
        HealthCheckProtocol="HTTPS",
        HealthCheckPort="8081",
        HealthCheckPath="/status",
        HealthCheckIntervalSeconds=10,
        HealthCheckTimeoutSeconds=10,
        HealthyThresholdCount=10,
        UnhealthyThresholdCount=4,
        Matcher={"HttpCode": "200-399"},
    )

    response = client.describe_target_groups(TargetGroupArns=[arn])
    response["TargetGroups"][0]["Matcher"]["HttpCode"].should.equal("200-399")
    response["TargetGroups"][0]["HealthCheckIntervalSeconds"].should.equal(10)
    response["TargetGroups"][0]["HealthCheckPath"].should.equal("/status")
    response["TargetGroups"][0]["HealthCheckPort"].should.equal("8081")
    response["TargetGroups"][0]["HealthCheckProtocol"].should.equal("HTTPS")
    response["TargetGroups"][0]["HealthCheckTimeoutSeconds"].should.equal(10)
    response["TargetGroups"][0]["HealthyThresholdCount"].should.equal(10)
    response["TargetGroups"][0]["UnhealthyThresholdCount"].should.equal(4)


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

    load_balancer_arn = response.get("LoadBalancers")[0].get("LoadBalancerArn")

    response = client.create_target_group(
        Name="a-target",
        Protocol="HTTP",
        Port=8080,
        VpcId=vpc.id,
        HealthCheckProtocol="HTTP",
        HealthCheckPort="8080",
        HealthCheckPath="/",
        HealthCheckIntervalSeconds=5,
        HealthCheckTimeoutSeconds=5,
        HealthyThresholdCount=5,
        UnhealthyThresholdCount=2,
        Matcher={"HttpCode": "200"},
    )
    target_group = response.get("TargetGroups")[0]
    target_group_arn = target_group["TargetGroupArn"]

    # Plain HTTP listener
    response = client.create_listener(
        LoadBalancerArn=load_balancer_arn,
        Protocol="HTTP",
        Port=80,
        DefaultActions=[{"Type": "forward", "TargetGroupArn": target_group_arn}],
    )
    listener_arn = response["Listeners"][0]["ListenerArn"]

    response = acm.request_certificate(
        DomainName="google.com",
        SubjectAlternativeNames=["google.com", "www.google.com", "mail.google.com"],
    )
    google_arn = response["CertificateArn"]
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
        Certificates=[{"CertificateArn": yahoo_arn,},],
        DefaultActions=[{"Type": "forward", "TargetGroupArn": target_group_arn}],
    )
    response["Listeners"][0]["Port"].should.equal(443)
    response["Listeners"][0]["Protocol"].should.equal("HTTPS")
    response["Listeners"][0]["SslPolicy"].should.equal(
        "ELBSecurityPolicy-TLS-1-2-2017-01"
    )
    len(response["Listeners"][0]["Certificates"]).should.equal(1)

    # Check default cert, can't do this in server mode
    if os.environ.get("TEST_SERVER_MODE", "false").lower() == "false":
        listener = (
            elbv2_backends["eu-central-1"]
            .load_balancers[load_balancer_arn]
            .listeners[listener_arn]
        )
        listener.certificate.should.equal(yahoo_arn)

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
    err["Code"].should.equal("CertificateWereNotPassed")
    err["Message"].should.equal(
        "You must provide a list containing exactly one certificate if the listener protocol is HTTPS."
    )

    # Bad cert
    with pytest.raises(ClientError):
        client.modify_listener(
            ListenerArn=listener_arn,
            Port=443,
            Protocol="HTTPS",
            SslPolicy="ELBSecurityPolicy-TLS-1-2-2017-01",
            Certificates=[{"CertificateArn": "lalala", "IsDefault": True}],
            DefaultActions=[{"Type": "forward", "TargetGroupArn": target_group_arn}],
        )


@mock_elbv2
@mock_ec2
def test_redirect_action_listener_rule():
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
        VpcId=vpc.id, CidrBlock="172.28.7.128/26", AvailabilityZone="us-east-1b"
    )

    response = conn.create_load_balancer(
        Name="my-lb",
        Subnets=[subnet1.id, subnet2.id],
        SecurityGroups=[security_group.id],
        Scheme="internal",
        Tags=[{"Key": "key_name", "Value": "a_value"}],
    )

    load_balancer_arn = response.get("LoadBalancers")[0].get("LoadBalancerArn")

    action = {
        "Type": "redirect",
        "RedirectConfig": {
            "Protocol": "HTTPS",
            "Port": "443",
            "StatusCode": "HTTP_301",
        },
    }

    response = conn.create_listener(
        LoadBalancerArn=load_balancer_arn,
        Protocol="HTTP",
        Port=80,
        DefaultActions=[action],
    )

    listener = response.get("Listeners")[0]
    expected_default_actions = [
        {
            "Type": "redirect",
            "RedirectConfig": {
                "Protocol": "HTTPS",
                "Port": "443",
                "StatusCode": "HTTP_301",
            },
        }
    ]
    listener.get("DefaultActions").should.equal(expected_default_actions)
    listener_arn = listener.get("ListenerArn")

    listener_response = conn.create_rule(
        ListenerArn=listener_arn,
        Conditions=[{"Field": "path-pattern", "Values": ["/*"]},],
        Priority=3,
        Actions=[action],
    )
    describe_rules_response = conn.describe_rules(ListenerArn=listener_arn)
    describe_rules_response["Rules"][0]["Actions"].should.equal(
        expected_default_actions
    )

    describe_listener_response = conn.describe_listeners(ListenerArns=[listener_arn])
    describe_listener_actions = describe_listener_response["Listeners"][0][
        "DefaultActions"
    ]
    describe_listener_actions.should.equal(expected_default_actions)

    modify_listener_response = conn.modify_listener(ListenerArn=listener_arn, Port=81)
    modify_listener_actions = modify_listener_response["Listeners"][0]["DefaultActions"]
    modify_listener_actions.should.equal(expected_default_actions)


@mock_elbv2
@mock_ec2
def test_cognito_action_listener_rule():
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
        VpcId=vpc.id, CidrBlock="172.28.7.128/26", AvailabilityZone="us-east-1b"
    )

    response = conn.create_load_balancer(
        Name="my-lb",
        Subnets=[subnet1.id, subnet2.id],
        SecurityGroups=[security_group.id],
        Scheme="internal",
        Tags=[{"Key": "key_name", "Value": "a_value"}],
    )
    load_balancer_arn = response.get("LoadBalancers")[0].get("LoadBalancerArn")

    action = {
        "Type": "authenticate-cognito",
        "AuthenticateCognitoConfig": {
            "UserPoolArn": "arn:aws:cognito-idp:us-east-1:{}:userpool/us-east-1_ABCD1234".format(
                ACCOUNT_ID
            ),
            "UserPoolClientId": "abcd1234abcd",
            "UserPoolDomain": "testpool",
        },
    }
    response = conn.create_listener(
        LoadBalancerArn=load_balancer_arn,
        Protocol="HTTP",
        Port=80,
        DefaultActions=[action],
    )

    listener = response.get("Listeners")[0]
    listener.get("DefaultActions")[0].should.equal(action)
    listener_arn = listener.get("ListenerArn")

    listener_response = conn.create_rule(
        ListenerArn=listener_arn,
        Conditions=[{"Field": "path-pattern", "Values": ["/*"]},],
        Priority=3,
        Actions=[action],
    )
    describe_rules_response = conn.describe_rules(ListenerArn=listener_arn)
    describe_rules_response["Rules"][0]["Actions"][0].should.equal(action)

    describe_listener_response = conn.describe_listeners(ListenerArns=[listener_arn])
    describe_listener_actions = describe_listener_response["Listeners"][0][
        "DefaultActions"
    ][0]
    describe_listener_actions.should.equal(action)


@mock_elbv2
@mock_ec2
def test_fixed_response_action_listener_rule():
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
        VpcId=vpc.id, CidrBlock="172.28.7.128/26", AvailabilityZone="us-east-1b"
    )

    response = conn.create_load_balancer(
        Name="my-lb",
        Subnets=[subnet1.id, subnet2.id],
        SecurityGroups=[security_group.id],
        Scheme="internal",
        Tags=[{"Key": "key_name", "Value": "a_value"}],
    )
    load_balancer_arn = response.get("LoadBalancers")[0].get("LoadBalancerArn")

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

    listener = response.get("Listeners")[0]
    listener.get("DefaultActions")[0].should.equal(action)
    listener_arn = listener.get("ListenerArn")

    listener_response = conn.create_rule(
        ListenerArn=listener_arn,
        Conditions=[{"Field": "path-pattern", "Values": ["/*"]},],
        Priority=3,
        Actions=[action],
    )
    describe_rules_response = conn.describe_rules(ListenerArn=listener_arn)
    describe_rules_response["Rules"][0]["Actions"][0].should.equal(action)

    describe_listener_response = conn.describe_listeners(ListenerArns=[listener_arn])
    describe_listener_actions = describe_listener_response["Listeners"][0][
        "DefaultActions"
    ][0]
    describe_listener_actions.should.equal(action)


@mock_elbv2
@mock_ec2
def test_fixed_response_action_listener_rule_validates_status_code():
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
        VpcId=vpc.id, CidrBlock="172.28.7.128/26", AvailabilityZone="us-east-1b"
    )

    response = conn.create_load_balancer(
        Name="my-lb",
        Subnets=[subnet1.id, subnet2.id],
        SecurityGroups=[security_group.id],
        Scheme="internal",
        Tags=[{"Key": "key_name", "Value": "a_value"}],
    )
    load_balancer_arn = response.get("LoadBalancers")[0].get("LoadBalancerArn")

    invalid_status_code_action = {
        "Type": "fixed-response",
        "FixedResponseConfig": {
            "ContentType": "text/plain",
            "MessageBody": "This page does not exist",
            "StatusCode": "100",
        },
    }

    with pytest.raises(ClientError) as invalid_status_code_exception:
        conn.create_listener(
            LoadBalancerArn=load_balancer_arn,
            Protocol="HTTP",
            Port=80,
            DefaultActions=[invalid_status_code_action],
        )

    invalid_status_code_exception.value.response["Error"]["Code"].should.equal(
        "ValidationError"
    )


@mock_elbv2
@mock_ec2
def test_fixed_response_action_listener_rule_validates_content_type():
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
        VpcId=vpc.id, CidrBlock="172.28.7.128/26", AvailabilityZone="us-east-1b"
    )

    response = conn.create_load_balancer(
        Name="my-lb",
        Subnets=[subnet1.id, subnet2.id],
        SecurityGroups=[security_group.id],
        Scheme="internal",
        Tags=[{"Key": "key_name", "Value": "a_value"}],
    )
    load_balancer_arn = response.get("LoadBalancers")[0].get("LoadBalancerArn")

    invalid_content_type_action = {
        "Type": "fixed-response",
        "FixedResponseConfig": {
            "ContentType": "Fake content type",
            "MessageBody": "This page does not exist",
            "StatusCode": "200",
        },
    }
    with pytest.raises(ClientError) as invalid_content_type_exception:
        conn.create_listener(
            LoadBalancerArn=load_balancer_arn,
            Protocol="HTTP",
            Port=80,
            DefaultActions=[invalid_content_type_action],
        )
    invalid_content_type_exception.value.response["Error"]["Code"].should.equal(
        "InvalidLoadBalancerAction"
    )
