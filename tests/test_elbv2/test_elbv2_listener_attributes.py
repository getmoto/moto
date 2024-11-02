import boto3
import pytest

from moto import mock_aws


@mock_aws
@pytest.mark.parametrize(
    "name,default_value,new_value", [("tcp.idle_timeout.seconds", "350", "360")]
)
def test_modify_listener_attributes(name, default_value, new_value):
    elbv2 = boto3.client("elbv2", "us-east-1")

    ec2 = boto3.resource("ec2", region_name="us-east-1")

    vpc = ec2.create_vpc(CidrBlock="172.28.7.0/24", InstanceTenancy="default")
    subnet1 = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="172.28.7.192/26", AvailabilityZone="us-east-1a"
    )

    response = elbv2.create_load_balancer(
        Name="my-lb", Subnets=[subnet1.id], Scheme="internal"
    )
    load_balancer_arn = response["LoadBalancers"][0]["LoadBalancerArn"]

    response = elbv2.create_target_group(
        Name="a-target", Protocol="HTTPS", Port=8443, VpcId=vpc.id
    )
    target_group = response["TargetGroups"][0]
    target_group_arn = target_group["TargetGroupArn"]

    listener_arn = elbv2.create_listener(
        LoadBalancerArn=load_balancer_arn,
        Protocol="HTTPS",
        Port=443,
        DefaultActions=[{"Type": "forward", "TargetGroupArn": target_group_arn}],
    )["Listeners"][0]["ListenerArn"]

    attrs = elbv2.describe_listener_attributes(ListenerArn=listener_arn)
    assert attrs["Attributes"] == [{"Key": name, "Value": default_value}]

    attrs = elbv2.modify_listener_attributes(
        ListenerArn=listener_arn, Attributes=[{"Key": name, "Value": new_value}]
    )
    assert attrs["Attributes"] == [{"Key": name, "Value": new_value}]

    attrs = elbv2.describe_listener_attributes(ListenerArn=listener_arn)
    assert attrs["Attributes"] == [{"Key": name, "Value": new_value}]
