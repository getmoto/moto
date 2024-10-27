from time import sleep
from uuid import uuid4

import boto3
import pytest
from botocore.exceptions import WaiterError

from . import elbv2_aws_verified


@elbv2_aws_verified()
@pytest.mark.aws_verified
def test_register_targets(target_is_aws=False):
    conn = boto3.client("elbv2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    ec2_client = boto3.client("ec2", region_name="us-east-1")

    lb_name = f"lb-{str(uuid4())[0:6]}"
    sg_name = f"sg{str(uuid4())[0:6]}"
    target_name = f"target-{str(uuid4())[0:6]}"

    ssm = boto3.client("ssm", "us-east-1")
    resp = ssm.get_parameters(
        Names=["/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-6.1-x86_64"]
    )
    ami = resp["Parameters"][0]["Value"]

    vpc = ec2.create_vpc(CidrBlock="172.28.7.0/24", InstanceTenancy="default")
    igw_id = ec2_client.create_internet_gateway()["InternetGateway"][
        "InternetGatewayId"
    ]
    vpc.attach_internet_gateway(InternetGatewayId=igw_id)
    route_table = vpc.create_route_table()
    route_table.create_route(DestinationCidrBlock="0.0.0.0/0", GatewayId=igw_id)
    security_group = ec2.create_security_group(
        GroupName=sg_name, Description="a", VpcId=vpc.id
    )

    ec2_client.authorize_security_group_ingress(
        GroupId=security_group.id,
        IpPermissions=[{"IpProtocol": "-1", "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}],
    )
    subnet1 = vpc.create_subnet(
        CidrBlock="172.28.7.192/26", AvailabilityZone="us-east-1a"
    )
    subnet2 = vpc.create_subnet(
        CidrBlock="172.28.7.0/26", AvailabilityZone="us-east-1b"
    )

    route_table.associate_with_subnet(SubnetId=subnet1.id)
    route_table.associate_with_subnet(SubnetId=subnet2.id)

    load_balancer_arn = listener_arn = target_group_arn = instance_id1 = (
        instance_id2
    ) = None

    try:
        # Init-script that starts Apache
        init_script = """#!/bin/bash
sudo yum update -y
sudo yum install -y httpd
sudo systemctl start httpd
sudo systemctl enable httpd"""

        # Start EC2 instances first, to give them time to get ready
        instance_id1 = ec2.create_instances(
            ImageId=ami,
            MinCount=1,
            MaxCount=1,
            KeyName="test2",
            NetworkInterfaces=[
                {
                    "DeviceIndex": 0,
                    "SubnetId": subnet1.id,
                    "AssociatePublicIpAddress": True,
                    "Groups": [security_group.id],
                }
            ],
            UserData=init_script,
        )[0].id
        instance_id2 = ec2.create_instances(
            ImageId=ami,
            MinCount=1,
            MaxCount=1,
            KeyName="test2",
            NetworkInterfaces=[
                {
                    "DeviceIndex": 0,
                    "SubnetId": subnet2.id,
                    "AssociatePublicIpAddress": True,
                    "Groups": [security_group.id],
                }
            ],
            UserData=init_script,
        )[0].id

        waiter = ec2_client.get_waiter("instance_running")
        waiter.wait(InstanceIds=[instance_id1, instance_id2])

        load_balancer_arn = conn.create_load_balancer(
            Name=lb_name,
            Subnets=[subnet1.id, subnet2.id],
            SecurityGroups=[security_group.id],
            Scheme="internal",
            Tags=[{"Key": "key_name", "Value": "a_value"}],
        )["LoadBalancers"][0]["LoadBalancerArn"]
        waiter = conn.get_waiter("load_balancer_available")
        waiter.wait(LoadBalancerArns=[load_balancer_arn])

        target_group_arn = conn.create_target_group(
            Name=target_name,
            Protocol="HTTP",
            Port=80,
            VpcId=vpc.id,
            HealthCheckProtocol="HTTP",
            HealthCheckPort="80",
            HealthCheckPath="/",
            HealthCheckIntervalSeconds=5,
            HealthCheckTimeoutSeconds=3,
            HealthyThresholdCount=5,
            UnhealthyThresholdCount=2,
            # Apache returns a 403 (with text: 'It Works!') by default if no other pages are available
            Matcher={"HttpCode": "403"},
        )["TargetGroups"][0]["TargetGroupArn"]

        # No targets registered yet
        healths = conn.describe_target_health(TargetGroupArn=target_group_arn)[
            "TargetHealthDescriptions"
        ]
        assert len(healths) == 0

        listener_arn = conn.create_listener(
            LoadBalancerArn=load_balancer_arn,
            Protocol="HTTP",
            Port=80,
            DefaultActions=[
                {
                    "Type": "forward",
                    "TargetGroupArn": target_group_arn,
                }
            ],
        )["Listeners"][0]["ListenerArn"]

        # Register target
        # Verify that they are healthy
        conn.register_targets(
            TargetGroupArn=target_group_arn,
            Targets=[{"Id": instance_id1}, {"Id": instance_id2}],
        )
        waiter = conn.get_waiter("target_in_service")
        waiter.wait(TargetGroupArn=target_group_arn)

        healths = conn.describe_target_health(TargetGroupArn=target_group_arn)[
            "TargetHealthDescriptions"
        ]
        assert {
            "Target": {"Id": instance_id1, "Port": 80},
            "HealthCheckPort": "80",
            "TargetHealth": {"State": "healthy"},
        } in healths
        assert {
            "Target": {"Id": instance_id2, "Port": 80},
            "HealthCheckPort": "80",
            "TargetHealth": {"State": "healthy"},
        } in healths

        # De-register target
        # Verify that they no longer appear when describing health
        conn.deregister_targets(
            TargetGroupArn=target_group_arn,
            Targets=[{"Id": instance_id1}],
        )
        waiter = conn.get_waiter("target_deregistered")
        waiter.wait(TargetGroupArn=target_group_arn, Targets=[{"Id": instance_id1}])

        healths = conn.describe_target_health(TargetGroupArn=target_group_arn)[
            "TargetHealthDescriptions"
        ]
        assert len(healths) == 1
        assert {
            "Target": {"Id": instance_id2, "Port": 80},
            "HealthCheckPort": "80",
            "TargetHealth": {"State": "healthy"},
        } in healths

        # We can explicitly request it's health though
        healths = conn.describe_target_health(
            TargetGroupArn=target_group_arn, Targets=[{"Id": instance_id1, "Port": 80}]
        )["TargetHealthDescriptions"]
        assert len(healths) == 1
        assert {
            "Target": {"Id": instance_id1, "Port": 80},
            "HealthCheckPort": "80",
            "TargetHealth": {
                "State": "unused",
                "Reason": "Target.NotRegistered",
                "Description": "Target is not registered to the target group",
            },
        } in healths

        # Re-register it, and stop the instance
        conn.register_targets(
            TargetGroupArn=target_group_arn,
            Targets=[{"Id": instance_id1}],
        )
        waiter = conn.get_waiter("target_in_service")
        waiter.wait(TargetGroupArn=target_group_arn)

        healths = conn.describe_target_health(TargetGroupArn=target_group_arn)[
            "TargetHealthDescriptions"
        ]
        assert {
            "Target": {"Id": instance_id1, "Port": 80},
            "HealthCheckPort": "80",
            "TargetHealth": {"State": "healthy"},
        } in healths
        assert {
            "Target": {"Id": instance_id2, "Port": 80},
            "HealthCheckPort": "80",
            "TargetHealth": {"State": "healthy"},
        } in healths

        ec2_client.stop_instances(InstanceIds=[instance_id1])
        waiter = ec2_client.get_waiter("instance_stopped")
        waiter.wait(InstanceIds=[instance_id1])

        # Instance is marked as 'unused' when stopped
        states = set()
        while states != {"healthy", "unused"}:
            healths = conn.describe_target_health(TargetGroupArn=target_group_arn)[
                "TargetHealthDescriptions"
            ]
            states = set([h["TargetHealth"]["State"] for h in healths])

            if target_is_aws:
                sleep(5)
        assert {
            "Target": {"Id": instance_id2, "Port": 80},
            "HealthCheckPort": "80",
            "TargetHealth": {"State": "healthy"},
        } in healths
        assert {
            "Target": {"Id": instance_id1, "Port": 80},
            "HealthCheckPort": "80",
            "TargetHealth": {
                "State": "unused",
                "Reason": "Target.InvalidState",
                "Description": "Target is in the stopped state",
            },
        } in healths

        ec2_client.terminate_instances(InstanceIds=[instance_id1])
        waiter = ec2_client.get_waiter("instance_terminated")
        waiter.wait(InstanceIds=[instance_id1])

        # Instance is removed when terminated
        healths = conn.describe_target_health(TargetGroupArn=target_group_arn)[
            "TargetHealthDescriptions"
        ]
        while len(healths) != 1:
            healths = conn.describe_target_health(TargetGroupArn=target_group_arn)[
                "TargetHealthDescriptions"
            ]

            if target_is_aws:
                sleep(5)

        assert {
            "Target": {"Id": instance_id2, "Port": 80},
            "HealthCheckPort": "80",
            "TargetHealth": {"State": "healthy"},
        } in healths

        # Terminated instances are marked as 'draining' until eternity (well - atleast 10 minutes)
        healths = conn.describe_target_health(
            TargetGroupArn=target_group_arn, Targets=[{"Id": instance_id1, "Port": 80}]
        )["TargetHealthDescriptions"]
        assert healths == [
            {
                "Target": {"Id": instance_id1, "Port": 80},
                "HealthCheckPort": "80",
                "TargetHealth": {
                    "State": "draining",
                    "Reason": "Target.DeregistrationInProgress",
                    "Description": "Target deregistration is in progress",
                },
            }
        ]

    finally:
        try:  # to delete instance1 - just in case it failed to stop earlier
            ec2_client.stop_instances(InstanceIds=[instance_id1])
            waiter = ec2_client.get_waiter("instance_stopped")
            waiter.wait(InstanceIds=[instance_id1])
            ec2_client.terminate_instances(InstanceIds=[instance_id1])
            waiter = ec2_client.get_waiter("instance_terminated")
            waiter.wait(InstanceIds=[instance_id1])
        except:  # noqa: E722 Do not use bare except
            pass

        if instance_id2:
            ec2_client.stop_instances(InstanceIds=[instance_id2])
            waiter = ec2_client.get_waiter("instance_stopped")
            waiter.wait(InstanceIds=[instance_id2])
            ec2_client.terminate_instances(InstanceIds=[instance_id2])
            waiter = ec2_client.get_waiter("instance_terminated")
            waiter.wait(InstanceIds=[instance_id2])

        if listener_arn:
            conn.delete_listener(ListenerArn=listener_arn)

        if target_group_arn:
            conn.delete_target_group(TargetGroupArn=target_group_arn)

        if load_balancer_arn:
            conn.delete_load_balancer(LoadBalancerArn=load_balancer_arn)
            try:
                waiter = conn.get_waiter("load_balancers_deleted")
                waiter.wait(LoadBalancerArns=[load_balancer_arn])
            except WaiterError:
                # This operations fails against botocore 1.35.15 and up
                # https://github.com/boto/botocore/issues/3252
                pass

    if target_is_aws:
        # Resources take a while to deregister
        # Wait, so we don't get DependencyViolations when deleting the SG
        sleep(30)

        security_group.delete()
        subnet1.delete()
        subnet2.delete()
        route_table.delete()
        ec2_client.detach_internet_gateway(InternetGatewayId=igw_id, VpcId=vpc.id)
        vpc.delete()
        ec2_client.delete_internet_gateway(InternetGatewayId=igw_id)


@elbv2_aws_verified()
@pytest.mark.aws_verified
def test_describe_unknown_targets(target_is_aws=False):
    conn = boto3.client("elbv2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    ec2_client = boto3.client("ec2", region_name="us-east-1")

    lb_name = f"lb-{str(uuid4())[0:6]}"
    sg_name = f"sg{str(uuid4())[0:6]}"
    target_name = f"target-{str(uuid4())[0:6]}"

    vpc = ec2.create_vpc(CidrBlock="172.28.7.0/24", InstanceTenancy="default")
    security_group = ec2.create_security_group(
        GroupName=sg_name, Description="a", VpcId=vpc.id
    )

    ec2_client.authorize_security_group_ingress(
        GroupId=security_group.id,
        IpPermissions=[{"IpProtocol": "-1", "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}],
    )
    subnet1 = vpc.create_subnet(
        CidrBlock="172.28.7.192/26", AvailabilityZone="us-east-1a"
    )
    subnet2 = vpc.create_subnet(
        CidrBlock="172.28.7.0/26", AvailabilityZone="us-east-1b"
    )

    load_balancer_arn = listener_arn = target_group_arn = None
    instance_id = "i-12345678901234567"

    try:
        load_balancer_arn = conn.create_load_balancer(
            Name=lb_name,
            Subnets=[subnet1.id, subnet2.id],
            SecurityGroups=[security_group.id],
            Scheme="internal",
            Tags=[{"Key": "key_name", "Value": "a_value"}],
        )["LoadBalancers"][0]["LoadBalancerArn"]
        waiter = conn.get_waiter("load_balancer_available")
        waiter.wait(LoadBalancerArns=[load_balancer_arn])

        target_group_arn = conn.create_target_group(
            Name=target_name,
            Protocol="HTTP",
            Port=80,
            VpcId=vpc.id,
            HealthCheckProtocol="HTTP",
            HealthCheckPort="80",
            HealthCheckPath="/",
            HealthCheckIntervalSeconds=5,
            HealthCheckTimeoutSeconds=3,
            HealthyThresholdCount=5,
            UnhealthyThresholdCount=2,
            # Apache returns a 403 (with text: 'It Works!') by default if no other pages are available
            Matcher={"HttpCode": "403"},
        )["TargetGroups"][0]["TargetGroupArn"]

        listener_arn = conn.create_listener(
            LoadBalancerArn=load_balancer_arn,
            Protocol="HTTP",
            Port=80,
            DefaultActions=[
                {
                    "Type": "forward",
                    "TargetGroupArn": target_group_arn,
                }
            ],
        )["Listeners"][0]["ListenerArn"]

        healths = conn.describe_target_health(
            TargetGroupArn=target_group_arn, Targets=[{"Id": instance_id}]
        )["TargetHealthDescriptions"]
        assert healths == [
            {
                "Target": {"Id": instance_id, "Port": 80},
                "HealthCheckPort": "80",
                "TargetHealth": {
                    "State": "unused",
                    "Reason": "Target.NotRegistered",
                    "Description": "Target is not registered to the target group",
                },
            }
        ]

    finally:
        if listener_arn:
            conn.delete_listener(ListenerArn=listener_arn)

        if target_group_arn:
            conn.delete_target_group(TargetGroupArn=target_group_arn)

        if load_balancer_arn:
            conn.delete_load_balancer(LoadBalancerArn=load_balancer_arn)
            try:
                waiter = conn.get_waiter("load_balancers_deleted")
                waiter.wait(LoadBalancerArns=[load_balancer_arn])
            except WaiterError:
                # This operations fails against botocore 1.35.15 and up
                # https://github.com/boto/botocore/issues/3252
                pass

    if target_is_aws:
        # Resources take a while to deregister
        # Wait, so we don't get DependencyViolations when deleting the SG
        sleep(30)

        security_group.delete()
        subnet1.delete()
        subnet2.delete()
        vpc.delete()
