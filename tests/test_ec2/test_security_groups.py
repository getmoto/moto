from __future__ import unicode_literals

import copy
import json
import unittest

import pytest

import boto3
import boto
import boto.ec2
from botocore.exceptions import ClientError
from boto.exception import EC2ResponseError
import sure  # noqa

from moto import mock_ec2, mock_ec2_deprecated, settings
from moto.ec2 import ec2_backend
from random import randint
from uuid import uuid4
from unittest import SkipTest


# Has boto3 equivalent
@mock_ec2_deprecated
def test_create_and_describe_security_group():
    conn = boto.connect_ec2("the_key", "the_secret")

    with pytest.raises(EC2ResponseError) as ex:
        security_group = conn.create_security_group(
            "test security group", "this is a test security group", dry_run=True
        )
    ex.value.error_code.should.equal("DryRunOperation")
    ex.value.status.should.equal(412)
    ex.value.message.should.equal(
        "An error occurred (DryRunOperation) when calling the CreateSecurityGroup operation: Request would have succeeded, but DryRun flag is set"
    )

    security_group = conn.create_security_group(
        "test security group", "this is a test security group"
    )

    security_group.name.should.equal("test security group")
    security_group.description.should.equal("this is a test security group")

    # Trying to create another group with the same name should throw an error
    with pytest.raises(EC2ResponseError) as cm:
        conn.create_security_group(
            "test security group", "this is a test security group"
        )
    cm.value.code.should.equal("InvalidGroup.Duplicate")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none

    all_groups = conn.get_all_security_groups()
    # The default group gets created automatically
    all_groups.should.have.length_of(2)
    group_names = [group.name for group in all_groups]
    set(group_names).should.equal(set(["default", "test security group"]))


@mock_ec2
def test_create_and_describe_security_group_boto3():
    ec2 = boto3.resource("ec2", "us-west-1")
    client = boto3.client("ec2", "us-west-1")

    with pytest.raises(ClientError) as ex:
        client.create_security_group(GroupName="test", Description="test", DryRun=True)
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the CreateSecurityGroup operation: Request would have succeeded, but DryRun flag is set"
    )

    sec_name = str(uuid4())
    security_group = ec2.create_security_group(GroupName=sec_name, Description="test")

    security_group.group_name.should.equal(sec_name)
    security_group.description.should.equal("test")

    # Trying to create another group with the same name should throw an error
    with pytest.raises(ClientError) as ex:
        client.create_security_group(GroupName=sec_name, Description="n/a")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal("InvalidGroup.Duplicate")

    all_groups = retrieve_all_sgs(client)
    # The default group gets created automatically
    [g["GroupId"] for g in all_groups].should.contain(security_group.id)
    group_names = set([group["GroupName"] for group in all_groups])
    group_names.should.contain("default")
    group_names.should.contain(sec_name)


# Has boto3 equivalent
@mock_ec2_deprecated
def test_create_security_group_without_description_raises_error():
    conn = boto.connect_ec2("the_key", "the_secret")

    with pytest.raises(EC2ResponseError) as cm:
        conn.create_security_group("test security group", "")
    cm.value.code.should.equal("MissingParameter")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none


@mock_ec2
def test_create_security_group_without_description_raises_error_boto3():
    ec2 = boto3.resource("ec2", "us-west-1")

    with pytest.raises(ClientError) as ex:
        ec2.create_security_group(GroupName="test security group", Description="")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal("MissingParameter")


# Has boto3 equivalent
@mock_ec2_deprecated
def test_default_security_group():
    conn = boto.ec2.connect_to_region("us-east-1")
    groups = conn.get_all_security_groups()
    groups.should.have.length_of(1)
    groups[0].name.should.equal("default")


@mock_ec2
def test_default_security_group_boto3():
    client = boto3.client("ec2", "us-west-1")
    groups = retrieve_all_sgs(client)
    [g["GroupName"] for g in groups].should.contain("default")


# Has boto3 equivalent
@mock_ec2_deprecated
def test_create_and_describe_vpc_security_group():
    conn = boto.connect_ec2("the_key", "the_secret")
    vpc_id = "vpc-5300000c"
    security_group = conn.create_security_group(
        "test security group", "this is a test security group", vpc_id=vpc_id
    )

    security_group.vpc_id.should.equal(vpc_id)

    security_group.name.should.equal("test security group")
    security_group.description.should.equal("this is a test security group")

    # Trying to create another group with the same name in the same VPC should
    # throw an error
    with pytest.raises(EC2ResponseError) as cm:
        conn.create_security_group(
            "test security group", "this is a test security group", vpc_id
        )
    cm.value.code.should.equal("InvalidGroup.Duplicate")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none

    all_groups = conn.get_all_security_groups(filters={"vpc-id": [vpc_id]})

    all_groups[0].vpc_id.should.equal(vpc_id)

    all_groups.should.have.length_of(1)
    all_groups[0].name.should.equal("test security group")


@mock_ec2
def test_create_and_describe_vpc_security_group_boto3():
    ec2 = boto3.resource("ec2", "us-west-1")
    client = boto3.client("ec2", "us-west-1")

    name = str(uuid4())
    vpc_id = f"vpc-{str(uuid4())[0:6]}"
    group_with = ec2.create_security_group(
        GroupName=name, Description="test", VpcId=vpc_id
    )

    group_with.vpc_id.should.equal(vpc_id)

    group_with.group_name.should.equal(name)
    group_with.description.should.equal("test")

    # Trying to create another group with the same name in the same VPC should
    # throw an error
    with pytest.raises(ClientError) as ex:
        ec2.create_security_group(GroupName=name, Description="n/a", VpcId=vpc_id)
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal("InvalidGroup.Duplicate")

    # Trying to create another group in the same name without VPC should pass
    group_without = ec2.create_security_group(
        GroupName=name, Description="non-vpc-group"
    )

    all_groups = retrieve_all_sgs(client)
    [a["GroupId"] for a in all_groups].should.contain(group_with.id)
    [a["GroupId"] for a in all_groups].should.contain(group_without.id)

    all_groups = client.describe_security_groups(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
    )["SecurityGroups"]

    all_groups.should.have.length_of(1)
    all_groups[0]["VpcId"].should.equal(vpc_id)
    all_groups[0]["GroupName"].should.equal(name)


# Has boto3 equivalent
@mock_ec2_deprecated
def test_create_two_security_groups_with_same_name_in_different_vpc():
    conn = boto.connect_ec2("the_key", "the_secret")
    vpc_id = "vpc-5300000c"
    vpc_id2 = "vpc-5300000d"

    conn.create_security_group(
        "test security group", "this is a test security group", vpc_id
    )
    conn.create_security_group(
        "test security group", "this is a test security group", vpc_id2
    )

    all_groups = conn.get_all_security_groups()

    all_groups.should.have.length_of(3)
    group_names = [group.name for group in all_groups]
    # The default group is created automatically
    set(group_names).should.equal(set(["default", "test security group"]))


@mock_ec2
def test_create_two_security_groups_with_same_name_in_different_vpc_boto3():
    ec2 = boto3.resource("ec2", "us-east-1")
    client = boto3.client("ec2", "us-east-1")

    name = str(uuid4())
    vpc_id = "vpc-5300000c"
    vpc_id2 = "vpc-5300000d"

    sg1 = ec2.create_security_group(GroupName=name, Description="n/a 1", VpcId=vpc_id)
    sg2 = ec2.create_security_group(GroupName=name, Description="n/a 2", VpcId=vpc_id2)

    all_groups = retrieve_all_sgs(client)
    group_ids = [group["GroupId"] for group in all_groups]
    group_ids.should.contain(sg1.id)
    group_ids.should.contain(sg2.id)

    group_names = [group["GroupName"] for group in all_groups]
    group_names.should.contain(name)


@mock_ec2
def test_create_two_security_groups_in_vpc_with_ipv6_enabled():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16", AmazonProvidedIpv6CidrBlock=True)

    security_group = ec2.create_security_group(
        GroupName=str(uuid4()), Description="Test security group sg01", VpcId=vpc.id
    )

    # The security group must have two defaul egress rules (one for ipv4 and aonther for ipv6)
    security_group.ip_permissions_egress.should.have.length_of(2)


# Has boto3 equivalent
@mock_ec2_deprecated
def test_deleting_security_groups():
    conn = boto.connect_ec2("the_key", "the_secret")
    security_group1 = conn.create_security_group("test1", "test1")
    conn.create_security_group("test2", "test2")

    conn.get_all_security_groups().should.have.length_of(3)

    # Deleting a group that doesn't exist should throw an error
    with pytest.raises(EC2ResponseError) as cm:
        conn.delete_security_group("foobar")
    cm.value.code.should.equal("InvalidGroup.NotFound")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none

    # Delete by name
    with pytest.raises(EC2ResponseError) as ex:
        conn.delete_security_group("test2", dry_run=True)
    ex.value.error_code.should.equal("DryRunOperation")
    ex.value.status.should.equal(412)
    ex.value.message.should.equal(
        "An error occurred (DryRunOperation) when calling the DeleteSecurityGroup operation: Request would have succeeded, but DryRun flag is set"
    )

    conn.delete_security_group("test2")
    conn.get_all_security_groups().should.have.length_of(2)

    # Delete by group id
    conn.delete_security_group(group_id=security_group1.id)
    conn.get_all_security_groups().should.have.length_of(1)


@mock_ec2
def test_deleting_security_groups_boto3():
    ec2 = boto3.resource("ec2", "us-west-1")
    client = boto3.client("ec2", "us-west-1")
    sg_name1 = str(uuid4())
    sg_name2 = str(uuid4())
    group1 = ec2.create_security_group(GroupName=sg_name1, Description="test desc 1")
    group2 = ec2.create_security_group(GroupName=sg_name2, Description="test desc 2")

    all_groups = retrieve_all_sgs(client)
    [g["GroupId"] for g in all_groups].should.contain(group1.id)
    [g["GroupId"] for g in all_groups].should.contain(group2.id)

    # Deleting a group that doesn't exist should throw an error
    with pytest.raises(ClientError) as ex:
        client.delete_security_group(GroupName="foobar")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal("InvalidGroup.NotFound")

    # Delete by name
    with pytest.raises(ClientError) as ex:
        client.delete_security_group(GroupName=sg_name2, DryRun=True)
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the DeleteSecurityGroup operation: Request would have succeeded, but DryRun flag is set"
    )

    client.delete_security_group(GroupName=sg_name2)

    all_groups = retrieve_all_sgs(client)
    [g["GroupId"] for g in all_groups].should.contain(group1.id)
    [g["GroupId"] for g in all_groups].shouldnt.contain(group2.id)

    # Delete by group id
    client.delete_security_group(GroupId=group1.id)

    all_groups = retrieve_all_sgs(client)
    [g["GroupId"] for g in all_groups].shouldnt.contain(group1.id)


# Has boto3 equivalent
@mock_ec2_deprecated
def test_delete_security_group_in_vpc():
    conn = boto.connect_ec2("the_key", "the_secret")
    vpc_id = "vpc-12345"
    security_group1 = conn.create_security_group("test1", "test1", vpc_id)

    # this should not throw an exception
    conn.delete_security_group(group_id=security_group1.id)


@mock_ec2
def test_delete_security_group_in_vpc_boto3():
    ec2 = boto3.resource("ec2", "us-west-1")
    client = boto3.client("ec2", "us-west-1")

    group = ec2.create_security_group(
        GroupName=str(uuid4()), Description="test1", VpcId="vpc-12345"
    )

    all_groups = retrieve_all_sgs(client)
    [g["GroupId"] for g in all_groups].should.contain(group.id)

    # this should not throw an exception
    client.delete_security_group(GroupId=group.id)

    all_groups = retrieve_all_sgs(client)
    [g["GroupId"] for g in all_groups].shouldnt.contain(group.id)


# Has boto3 equivalent
@mock_ec2_deprecated
def test_authorize_ip_range_and_revoke():
    conn = boto.connect_ec2("the_key", "the_secret")
    security_group = conn.create_security_group("test", "test")

    with pytest.raises(EC2ResponseError) as ex:
        success = security_group.authorize(
            ip_protocol="tcp",
            from_port="22",
            to_port="2222",
            cidr_ip="123.123.123.123/32",
            dry_run=True,
        )
    ex.value.error_code.should.equal("DryRunOperation")
    ex.value.status.should.equal(412)
    ex.value.message.should.equal(
        "An error occurred (DryRunOperation) when calling the GrantSecurityGroupIngress operation: Request would have succeeded, but DryRun flag is set"
    )

    success = security_group.authorize(
        ip_protocol="tcp", from_port="22", to_port="2222", cidr_ip="123.123.123.123/32"
    )
    assert success.should.be.true

    security_group = conn.get_all_security_groups(groupnames=["test"])[0]
    int(security_group.rules[0].to_port).should.equal(2222)
    security_group.rules[0].grants[0].cidr_ip.should.equal("123.123.123.123/32")

    # Wrong Cidr should throw error
    with pytest.raises(EC2ResponseError) as cm:
        security_group.revoke(
            ip_protocol="tcp",
            from_port="22",
            to_port="2222",
            cidr_ip="123.123.123.122/32",
        )
    cm.value.code.should.equal("InvalidPermission.NotFound")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none

    # Actually revoke
    with pytest.raises(EC2ResponseError) as ex:
        security_group.revoke(
            ip_protocol="tcp",
            from_port="22",
            to_port="2222",
            cidr_ip="123.123.123.123/32",
            dry_run=True,
        )
    ex.value.error_code.should.equal("DryRunOperation")
    ex.value.status.should.equal(412)
    ex.value.message.should.equal(
        "An error occurred (DryRunOperation) when calling the RevokeSecurityGroupIngress operation: Request would have succeeded, but DryRun flag is set"
    )

    security_group.revoke(
        ip_protocol="tcp", from_port="22", to_port="2222", cidr_ip="123.123.123.123/32"
    )

    security_group = conn.get_all_security_groups()[0]
    security_group.rules.should.have.length_of(0)

    # Test for egress as well
    vpc_conn = boto.connect_vpc()
    vpc = vpc_conn.create_vpc("10.0.0.0/16")
    egress_security_group = conn.create_security_group(
        "testegress", "testegress", vpc_id=vpc.id
    )

    with pytest.raises(EC2ResponseError) as ex:
        success = conn.authorize_security_group_egress(
            egress_security_group.id,
            "tcp",
            from_port="22",
            to_port="2222",
            cidr_ip="123.123.123.123/32",
            dry_run=True,
        )
    ex.value.error_code.should.equal("DryRunOperation")
    ex.value.status.should.equal(412)
    ex.value.message.should.equal(
        "An error occurred (DryRunOperation) when calling the GrantSecurityGroupEgress operation: Request would have succeeded, but DryRun flag is set"
    )

    success = conn.authorize_security_group_egress(
        egress_security_group.id,
        "tcp",
        from_port="22",
        to_port="2222",
        cidr_ip="123.123.123.123/32",
    )
    assert success.should.be.true
    egress_security_group = conn.get_all_security_groups(groupnames="testegress")[0]
    # There are two egress rules associated with the security group:
    # the default outbound rule and the new one
    int(egress_security_group.rules_egress[1].to_port).should.equal(2222)
    actual_cidr = egress_security_group.rules_egress[1].grants[0].cidr_ip
    actual_cidr.should.equal("123.123.123.123/32")

    # Wrong Cidr should throw error
    egress_security_group.revoke.when.called_with(
        ip_protocol="tcp", from_port="22", to_port="2222", cidr_ip="123.123.123.122/32"
    ).should.throw(EC2ResponseError)

    # Actually revoke
    with pytest.raises(EC2ResponseError) as ex:
        conn.revoke_security_group_egress(
            egress_security_group.id,
            "tcp",
            from_port="22",
            to_port="2222",
            cidr_ip="123.123.123.123/32",
            dry_run=True,
        )
    ex.value.error_code.should.equal("DryRunOperation")
    ex.value.status.should.equal(412)
    ex.value.message.should.equal(
        "An error occurred (DryRunOperation) when calling the RevokeSecurityGroupEgress operation: Request would have succeeded, but DryRun flag is set"
    )

    conn.revoke_security_group_egress(
        egress_security_group.id,
        "tcp",
        from_port="22",
        to_port="2222",
        cidr_ip="123.123.123.123/32",
    )

    egress_security_group = [
        group
        for group in conn.get_all_security_groups()
        if group.id == egress_security_group.id
    ][0]
    # There is still the default outbound rule
    egress_security_group.rules_egress.should.have.length_of(1)


@mock_ec2
def test_authorize_ip_range_and_revoke_boto3():
    ec2 = boto3.resource("ec2", "us-west-1")
    client = boto3.client("ec2", "us-west-1")
    security_group = ec2.create_security_group(
        GroupName=str(uuid4()), Description="test"
    )

    with pytest.raises(ClientError) as ex:
        security_group.authorize_ingress(
            IpProtocol="tcp",
            FromPort=22,
            ToPort=2222,
            CidrIp="123.123.123.123/32",
            DryRun=True,
        )
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the GrantSecurityGroupIngress operation: Request would have succeeded, but DryRun flag is set"
    )

    ingress_permissions = [
        {
            "IpProtocol": "tcp",
            "FromPort": 22,
            "ToPort": 2222,
            "IpRanges": [{"CidrIp": "123.123.123.123/32"}],
        }
    ]

    security_group.authorize_ingress(IpPermissions=ingress_permissions)

    security_group.ip_permissions.should.have.length_of(1)
    security_group.ip_permissions[0]["ToPort"].should.equal(2222)
    security_group.ip_permissions[0]["IpProtocol"].should.equal("tcp")
    security_group.ip_permissions[0]["IpRanges"].should.equal(
        [{"CidrIp": "123.123.123.123/32"}]
    )

    # Wrong Cidr should throw error
    with pytest.raises(ClientError) as ex:
        wrong_permissions = copy.deepcopy(ingress_permissions)
        wrong_permissions[0]["IpRanges"][0]["CidrIp"] = "123.123.123.122/32"
        security_group.revoke_ingress(IpPermissions=wrong_permissions)
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal("InvalidPermission.NotFound")

    # Actually revoke
    with pytest.raises(ClientError) as ex:
        security_group.revoke_ingress(IpPermissions=ingress_permissions, DryRun=True)
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the RevokeSecurityGroupIngress operation: Request would have succeeded, but DryRun flag is set"
    )

    security_group.revoke_ingress(IpPermissions=ingress_permissions)

    security_group.ip_permissions.should.have.length_of(0)

    # Test for egress as well
    egress_security_group = ec2.create_security_group(
        GroupName=str(uuid4()), Description="desc", VpcId="vpc-3432589"
    )
    egress_permissions = [
        {
            "IpProtocol": "tcp",
            "FromPort": 22,
            "ToPort": 2222,
            "IpRanges": [{"CidrIp": "123.123.123.123/32"}],
        }
    ]

    with pytest.raises(ClientError) as ex:
        egress_security_group.authorize_egress(
            IpPermissions=egress_permissions, DryRun=True
        )
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the GrantSecurityGroupEgress operation: Request would have succeeded, but DryRun flag is set"
    )

    egress_security_group.authorize_egress(IpPermissions=egress_permissions)

    egress_security_group.ip_permissions_egress[0]["FromPort"].should.equal(22)
    egress_security_group.ip_permissions_egress[0]["IpProtocol"].should.equal("tcp")
    egress_security_group.ip_permissions_egress[0]["ToPort"].should.equal(2222)
    egress_security_group.ip_permissions_egress[0]["IpRanges"].should.equal(
        [{"CidrIp": "123.123.123.123/32"}]
    )

    # Wrong Cidr should throw error
    with pytest.raises(ClientError) as ex:
        wrong_permissions = copy.deepcopy(egress_permissions)
        wrong_permissions[0]["IpRanges"][0]["CidrIp"] = "123.123.123.122/32"
        security_group.revoke_egress(IpPermissions=wrong_permissions)
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal("InvalidPermission.NotFound")

    # Actually revoke
    with pytest.raises(ClientError) as ex:
        egress_security_group.revoke_egress(
            IpPermissions=egress_permissions, DryRun=True,
        )
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the RevokeSecurityGroupEgress operation: Request would have succeeded, but DryRun flag is set"
    )

    egress_security_group.revoke_egress(IpPermissions=egress_permissions)

    egress_security_group = client.describe_security_groups()["SecurityGroups"][0]
    # There is still the default outbound rule
    egress_security_group["IpPermissionsEgress"].should.have.length_of(1)


# Has boto3 equivalent
@mock_ec2_deprecated
def test_authorize_other_group_and_revoke():
    conn = boto.connect_ec2("the_key", "the_secret")
    security_group = conn.create_security_group("test", "test")
    other_security_group = conn.create_security_group("other", "other")
    wrong_group = conn.create_security_group("wrong", "wrong")

    success = security_group.authorize(
        ip_protocol="tcp",
        from_port="22",
        to_port="2222",
        src_group=other_security_group,
    )
    assert success.should.be.true

    security_group = [
        group for group in conn.get_all_security_groups() if group.name == "test"
    ][0]
    int(security_group.rules[0].to_port).should.equal(2222)
    security_group.rules[0].grants[0].group_id.should.equal(other_security_group.id)

    # Wrong source group should throw error
    with pytest.raises(EC2ResponseError) as cm:
        security_group.revoke(
            ip_protocol="tcp", from_port="22", to_port="2222", src_group=wrong_group
        )
    cm.value.code.should.equal("InvalidPermission.NotFound")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none

    # Actually revoke
    security_group.revoke(
        ip_protocol="tcp",
        from_port="22",
        to_port="2222",
        src_group=other_security_group,
    )

    security_group = [
        group for group in conn.get_all_security_groups() if group.name == "test"
    ][0]
    security_group.rules.should.have.length_of(0)


@mock_ec2
def test_authorize_other_group_and_revoke_boto3():
    ec2 = boto3.resource("ec2", "us-west-1")
    client = boto3.client("ec2", "us-west-1")
    sg_name = str(uuid4())
    security_group = ec2.create_security_group(
        GroupName=sg_name, Description="test desc"
    )
    other_security_group = ec2.create_security_group(
        GroupName=str(uuid4()), Description="other"
    )
    ec2.create_security_group(GroupName=str(uuid4()), Description="wrong")

    # Note: Should be easier to use the SourceSecurityGroupNames-parameter, but that's not supported atm
    permissions = [
        {
            "IpProtocol": "tcp",
            "FromPort": 22,
            "ToPort": 2222,
            "UserIdGroupPairs": [
                {
                    "GroupId": other_security_group.id,
                    "GroupName": other_security_group.group_name,
                    "UserId": other_security_group.owner_id,
                }
            ],
        }
    ]
    security_group.authorize_ingress(IpPermissions=permissions)

    found_sec_group = client.describe_security_groups(GroupNames=[sg_name])[
        "SecurityGroups"
    ][0]
    found_sec_group["IpPermissions"][0]["ToPort"].should.equal(2222)
    found_sec_group["IpPermissions"][0]["UserIdGroupPairs"][0]["GroupId"].should.equal(
        other_security_group.id
    )

    # Wrong source group should throw error
    with pytest.raises(ClientError) as ex:
        wrong_permissions = copy.deepcopy(permissions)
        wrong_permissions[0]["UserIdGroupPairs"][0]["GroupId"] = "unknown"
        security_group.revoke_ingress(IpPermissions=wrong_permissions)
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal("InvalidGroup.NotFound")

    # Actually revoke
    security_group.revoke_ingress(IpPermissions=permissions)

    found_sec_group = client.describe_security_groups(GroupNames=[sg_name])[
        "SecurityGroups"
    ][0]
    found_sec_group["IpPermissions"].should.have.length_of(0)


@mock_ec2
def test_authorize_other_group_egress_and_revoke():
    ec2 = boto3.resource("ec2", region_name="us-west-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")

    sg01 = ec2.create_security_group(
        GroupName=str(uuid4()), Description="Test security group sg01", VpcId=vpc.id
    )
    sg02 = ec2.create_security_group(
        GroupName=str(uuid4()), Description="Test security group sg02", VpcId=vpc.id
    )

    ip_permission = {
        "IpProtocol": "tcp",
        "FromPort": 27017,
        "ToPort": 27017,
        "UserIdGroupPairs": [
            {"GroupId": sg02.id, "GroupName": "sg02", "UserId": sg02.owner_id}
        ],
        "IpRanges": [],
        "Ipv6Ranges": [],
        "PrefixListIds": [],
    }
    org_ip_permission = ip_permission.copy()
    ip_permission["UserIdGroupPairs"][0].pop("GroupName")

    sg01.authorize_egress(IpPermissions=[org_ip_permission])
    sg01.ip_permissions_egress.should.have.length_of(2)
    sg01.ip_permissions_egress.should.contain(ip_permission)

    sg01.revoke_egress(IpPermissions=[org_ip_permission])
    sg01.ip_permissions_egress.should.have.length_of(1)


# Has boto3 equivalent
@mock_ec2_deprecated
def test_authorize_group_in_vpc():
    conn = boto.connect_ec2("the_key", "the_secret")
    vpc_id = "vpc-12345"

    # create 2 groups in a vpc
    security_group = conn.create_security_group("test1", "test1", vpc_id)
    other_security_group = conn.create_security_group("test2", "test2", vpc_id)

    success = security_group.authorize(
        ip_protocol="tcp",
        from_port="22",
        to_port="2222",
        src_group=other_security_group,
    )
    success.should.be.true

    # Check that the rule is accurate
    security_group = [
        group for group in conn.get_all_security_groups() if group.name == "test1"
    ][0]
    int(security_group.rules[0].to_port).should.equal(2222)
    security_group.rules[0].grants[0].group_id.should.equal(other_security_group.id)

    # Now remove the rule
    success = security_group.revoke(
        ip_protocol="tcp",
        from_port="22",
        to_port="2222",
        src_group=other_security_group,
    )
    success.should.be.true

    # And check that it gets revoked
    security_group = [
        group for group in conn.get_all_security_groups() if group.name == "test1"
    ][0]
    security_group.rules.should.have.length_of(0)


@mock_ec2
def test_authorize_group_in_vpc_boto3():
    ec2 = boto3.resource("ec2", "ap-south-1")
    client = boto3.client("ec2", region_name="ap-south-1")
    vpc_id = "vpc-12345"

    # create 2 groups in a vpc
    sec_name1 = str(uuid4())
    sec_name2 = str(uuid4())
    security_group = ec2.create_security_group(
        GroupName=sec_name1, Description="test desc 1", VpcId=vpc_id
    )
    other_security_group = ec2.create_security_group(
        GroupName=sec_name2, Description="test desc 2", VpcId=vpc_id
    )

    permissions = [
        {
            "IpProtocol": "tcp",
            "FromPort": 22,
            "ToPort": 2222,
            "UserIdGroupPairs": [
                {
                    "GroupId": other_security_group.id,
                    "GroupName": other_security_group.group_name,
                    "UserId": other_security_group.owner_id,
                }
            ],
        }
    ]
    security_group.authorize_ingress(IpPermissions=permissions)

    # Check that the rule is accurate
    found_sec_group = client.describe_security_groups(GroupNames=[sec_name1])[
        "SecurityGroups"
    ][0]
    found_sec_group["IpPermissions"][0]["ToPort"].should.equal(2222)
    found_sec_group["IpPermissions"][0]["UserIdGroupPairs"][0]["GroupId"].should.equal(
        other_security_group.id
    )

    # Now remove the rule
    security_group.revoke_ingress(IpPermissions=permissions)

    # And check that it gets revoked
    found_sec_group = client.describe_security_groups(GroupNames=[sec_name1])[
        "SecurityGroups"
    ][0]
    found_sec_group["IpPermissions"].should.have.length_of(0)


# Has boto3 equivalent
@mock_ec2_deprecated
def test_get_all_security_groups():
    conn = boto.connect_ec2()
    sg1 = conn.create_security_group(
        name="test1", description="test1", vpc_id="vpc-mjm05d27"
    )
    conn.create_security_group(name="test2", description="test2")

    resp = conn.get_all_security_groups(groupnames=["test1"])
    resp.should.have.length_of(1)
    resp[0].id.should.equal(sg1.id)

    with pytest.raises(EC2ResponseError) as cm:
        conn.get_all_security_groups(groupnames=["does_not_exist"])
    cm.value.code.should.equal("InvalidGroup.NotFound")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none

    resp.should.have.length_of(1)
    resp[0].id.should.equal(sg1.id)

    resp = conn.get_all_security_groups(filters={"vpc-id": ["vpc-mjm05d27"]})
    resp.should.have.length_of(1)
    resp[0].id.should.equal(sg1.id)

    resp = conn.get_all_security_groups(filters={"vpc-id": ["vpc-mjm05d27"]})
    resp.should.have.length_of(1)
    resp[0].id.should.equal(sg1.id)

    resp = conn.get_all_security_groups(filters={"description": ["test1"]})
    resp.should.have.length_of(1)
    resp[0].id.should.equal(sg1.id)

    resp = conn.get_all_security_groups()
    resp.should.have.length_of(3)


@mock_ec2
def test_describe_security_groups():
    ec2 = boto3.resource("ec2", "us-west-1")
    client = boto3.client("ec2", "us-west-1")
    vpc_id = f"vpc-{str(uuid4())[0:6]}"
    name_1 = str(uuid4())
    desc_1 = str(uuid4())
    sg1 = ec2.create_security_group(GroupName=name_1, Description=desc_1, VpcId=vpc_id)
    sg2 = ec2.create_security_group(GroupName=str(uuid4()), Description="test desc 2")

    resp = client.describe_security_groups(GroupNames=[name_1])["SecurityGroups"]
    resp.should.have.length_of(1)
    resp[0].should.have.key("GroupId").equal(sg1.id)

    with pytest.raises(ClientError) as ex:
        client.describe_security_groups(GroupNames=["does_not_exist"])
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal("InvalidGroup.NotFound")

    resp = client.describe_security_groups(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
    )["SecurityGroups"]
    resp.should.have.length_of(1)
    resp[0].should.have.key("GroupId").equal(sg1.id)

    resp = client.describe_security_groups(
        Filters=[{"Name": "description", "Values": [desc_1]}]
    )["SecurityGroups"]
    resp.should.have.length_of(1)
    resp[0].should.have.key("GroupId").equal(sg1.id)

    all_sgs = retrieve_all_sgs(client)
    sg_ids = [sg["GroupId"] for sg in all_sgs]
    sg_ids.should.contain(sg1.id)
    sg_ids.should.contain(sg2.id)


# Has boto3 equivalent
@mock_ec2_deprecated
def test_authorize_bad_cidr_throws_invalid_parameter_value():
    conn = boto.connect_ec2("the_key", "the_secret")
    security_group = conn.create_security_group("test", "test")
    with pytest.raises(EC2ResponseError) as cm:
        security_group.authorize(
            ip_protocol="tcp", from_port="22", to_port="2222", cidr_ip="123.123.123.123"
        )
    cm.value.code.should.equal("InvalidParameterValue")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none


@mock_ec2
def test_authorize_bad_cidr_throws_invalid_parameter_value_boto3():
    ec2 = boto3.resource("ec2", "us-west-1")
    sec_group = ec2.create_security_group(GroupName=str(uuid4()), Description="test")
    with pytest.raises(ClientError) as ex:
        permissions = [
            {
                "IpProtocol": "tcp",
                "FromPort": 22,
                "ToPort": 2222,
                "IpRanges": [{"CidrIp": "123.123.123.123"}],
            }
        ]
        sec_group.authorize_ingress(IpPermissions=permissions)
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal("InvalidParameterValue")


# Has boto3 equivalent
@mock_ec2_deprecated
def test_security_group_tagging():
    conn = boto.connect_vpc()
    vpc = conn.create_vpc("10.0.0.0/16")

    sg = conn.create_security_group("test-sg", "Test SG", vpc.id)

    with pytest.raises(EC2ResponseError) as ex:
        sg.add_tag("Test", "Tag", dry_run=True)
    ex.value.error_code.should.equal("DryRunOperation")
    ex.value.status.should.equal(412)
    ex.value.message.should.equal(
        "An error occurred (DryRunOperation) when calling the CreateTags operation: Request would have succeeded, but DryRun flag is set"
    )

    sg.add_tag("Test", "Tag")

    tag = conn.get_all_tags()[0]
    tag.name.should.equal("Test")
    tag.value.should.equal("Tag")

    group = conn.get_all_security_groups("test-sg")[0]
    group.tags.should.have.length_of(1)
    group.tags["Test"].should.equal("Tag")


# Has boto3 equivalent
@mock_ec2_deprecated
def test_security_group_tag_filtering():
    conn = boto.connect_ec2()
    sg = conn.create_security_group("test-sg", "Test SG")
    sg.add_tag("test-tag", "test-value")

    groups = conn.get_all_security_groups(filters={"tag:test-tag": "test-value"})
    groups.should.have.length_of(1)


@mock_ec2
def test_security_group_tag_filtering_boto3():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    client = boto3.client("ec2", region_name="us-east-1")
    sg = ec2.create_security_group(GroupName=str(uuid4()), Description="Test SG")
    tag_name = str(uuid4())[0:6]
    tag_val = str(uuid4())
    sg.create_tags(Tags=[{"Key": tag_name, "Value": tag_val}])

    groups = client.describe_security_groups(
        Filters=[{"Name": f"tag:{tag_name}", "Values": [tag_val]}]
    )["SecurityGroups"]
    groups.should.have.length_of(1)

    groups = client.describe_security_groups(
        Filters=[{"Name": f"tag:{tag_name}", "Values": ["unknown"]}]
    )["SecurityGroups"]
    groups.should.have.length_of(0)


# Has boto3 equivalent
@mock_ec2_deprecated
def test_authorize_all_protocols_with_no_port_specification():
    conn = boto.connect_ec2()
    sg = conn.create_security_group("test", "test")

    success = sg.authorize(ip_protocol="-1", cidr_ip="0.0.0.0/0")
    success.should.be.true

    sg = conn.get_all_security_groups("test")[0]
    sg.rules[0].from_port.should.equal(None)
    sg.rules[0].to_port.should.equal(None)


@mock_ec2
def test_authorize_all_protocols_with_no_port_specification_boto3():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    client = boto3.client("ec2", region_name="us-east-1")
    sg_name = str(uuid4())
    sg = ec2.create_security_group(GroupName=sg_name, Description="test desc")

    permissions = [{"IpProtocol": "-1", "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}]
    sg.authorize_ingress(IpPermissions=permissions)

    sg = client.describe_security_groups(GroupNames=[sg_name])["SecurityGroups"][0]
    permission = sg["IpPermissions"][0]
    permission.should.have.key("IpProtocol").equal("-1")
    permission.should.have.key("IpRanges").equal([{"CidrIp": "0.0.0.0/0"}])
    permission.shouldnt.have.key("FromPort")
    permission.shouldnt.have.key("ToPort")


# Has boto3 equivalent
@mock_ec2_deprecated
def test_sec_group_rule_limit():
    ec2_conn = boto.connect_ec2()
    sg = ec2_conn.create_security_group("test", "test")
    other_sg = ec2_conn.create_security_group("test_2", "test_other")

    # INGRESS
    with pytest.raises(EC2ResponseError) as cm:
        ec2_conn.authorize_security_group(
            group_id=sg.id,
            ip_protocol="-1",
            cidr_ip=["{0}.0.0.0/0".format(i) for i in range(110)],
        )
    cm.value.error_code.should.equal("RulesPerSecurityGroupLimitExceeded")

    sg.rules.should.be.empty
    # authorize a rule targeting a different sec group (because this count too)
    success = ec2_conn.authorize_security_group(
        group_id=sg.id, ip_protocol="-1", src_security_group_group_id=other_sg.id
    )
    success.should.be.true
    # fill the rules up the limit
    success = ec2_conn.authorize_security_group(
        group_id=sg.id,
        ip_protocol="-1",
        cidr_ip=["{0}.0.0.0/0".format(i) for i in range(1, 60)],
    )
    success.should.be.true
    # verify that we cannot authorize past the limit for a CIDR IP
    with pytest.raises(EC2ResponseError) as cm:
        ec2_conn.authorize_security_group(
            group_id=sg.id, ip_protocol="-1", cidr_ip=["100.0.0.0/0"]
        )
    cm.value.error_code.should.equal("RulesPerSecurityGroupLimitExceeded")
    # verify that we cannot authorize past the limit for a different sec group
    with pytest.raises(EC2ResponseError) as cm:
        ec2_conn.authorize_security_group(
            group_id=sg.id, ip_protocol="-1", src_security_group_group_id=other_sg.id
        )
    cm.value.error_code.should.equal("RulesPerSecurityGroupLimitExceeded")

    # EGRESS
    # authorize a rule targeting a different sec group (because this count too)
    ec2_conn.authorize_security_group_egress(
        group_id=sg.id, ip_protocol="-1", src_group_id=other_sg.id
    )
    # fill the rules up the limit, 59 + 1 default rule
    for i in range(1, 59):
        ec2_conn.authorize_security_group_egress(
            group_id=sg.id, ip_protocol="-1", cidr_ip="{0}.0.0.0/0".format(i)
        )
    # verify that we cannot authorize past the limit for a CIDR IP
    with pytest.raises(EC2ResponseError) as cm:
        ec2_conn.authorize_security_group_egress(
            group_id=sg.id, ip_protocol="-1", cidr_ip="101.0.0.0/0"
        )
    cm.value.error_code.should.equal("RulesPerSecurityGroupLimitExceeded")
    # verify that we cannot authorize past the limit for a different sec group
    with pytest.raises(EC2ResponseError) as cm:
        ec2_conn.authorize_security_group_egress(
            group_id=sg.id, ip_protocol="-1", src_group_id=other_sg.id
        )
    cm.value.error_code.should.equal("RulesPerSecurityGroupLimitExceeded")


@mock_ec2
@pytest.mark.parametrize(
    "use_vpc", [True, False], ids=["Use VPC", "Without VPC"],
)
def test_sec_group_rule_limit_boto3(use_vpc):
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")

    limit = 60
    if use_vpc:
        vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
        sg = ec2.create_security_group(
            GroupName=str(uuid4()), Description="test", VpcId=vpc.id
        )
        other_sg = ec2.create_security_group(
            GroupName=str(uuid4()), Description="test_other", VpcId=vpc.id
        )
    else:
        sg = ec2.create_security_group(GroupName=str(uuid4()), Description="test")
        other_sg = ec2.create_security_group(
            GroupName=str(uuid4()), Description="test_other"
        )

    # INGRESS
    with pytest.raises(ClientError) as ex:
        ip_permissions = [
            {
                "IpProtocol": "-1",
                "IpRanges": [{"CidrIp": "{}.0.0.0/0".format(i)} for i in range(110)],
            }
        ]
        client.authorize_security_group_ingress(
            GroupId=sg.id, IpPermissions=ip_permissions
        )
    ex.value.response["Error"]["Code"].should.equal(
        "RulesPerSecurityGroupLimitExceeded"
    )

    sg.reload()
    sg.ip_permissions.should.be.empty
    # authorize a rule targeting a different sec group (because this count too)
    other_permissions = [
        {
            "IpProtocol": "-1",
            "UserIdGroupPairs": [
                {
                    "GroupId": other_sg.id,
                    "GroupName": other_sg.group_name,
                    "UserId": other_sg.owner_id,
                }
            ],
        }
    ]
    client.authorize_security_group_ingress(
        GroupId=sg.id, IpPermissions=other_permissions
    )
    # fill the rules up the limit
    permissions = [
        {
            "IpProtocol": "-1",
            "IpRanges": [{"CidrIp": "{}.0.0.0/0".format(i)} for i in range(limit - 1)],
        }
    ]
    client.authorize_security_group_ingress(GroupId=sg.id, IpPermissions=permissions)
    # verify that we cannot authorize past the limit for a CIDR IP
    with pytest.raises(ClientError) as ex:
        permissions = [{"IpProtocol": "-1", "IpRanges": [{"CidrIp": "100.0.0.0/0"}],}]
        client.authorize_security_group_ingress(
            GroupId=sg.id, IpPermissions=permissions
        )
    ex.value.response["Error"]["Code"].should.equal(
        "RulesPerSecurityGroupLimitExceeded"
    )
    # verify that we cannot authorize past the limit for a different sec group
    with pytest.raises(ClientError) as ex:
        client.authorize_security_group_ingress(
            GroupId=sg.id, IpPermissions=other_permissions
        )
    ex.value.response["Error"]["Code"].should.equal(
        "RulesPerSecurityGroupLimitExceeded"
    )

    # EGRESS
    # authorize a rule targeting a different sec group (because this count too)
    client.authorize_security_group_egress(
        GroupId=sg.id, IpPermissions=other_permissions
    )
    # fill the rules up the limit
    # remember that by default, when created a sec group contains 1 egress rule
    # so our other_sg rule + 98 CIDR IP rules + 1 by default == 100 the limit
    permissions = [
        {
            "IpProtocol": "-1",
            "IpRanges": [
                {"CidrIp": "{}.0.0.0/0".format(i)} for i in range(1, limit - 1)
            ],
        }
    ]
    client.authorize_security_group_egress(GroupId=sg.id, IpPermissions=permissions)
    # verify that we cannot authorize past the limit for a CIDR IP
    with pytest.raises(ClientError) as ex:
        permissions = [{"IpProtocol": "-1", "IpRanges": [{"CidrIp": "101.0.0.0/0"}],}]
        client.authorize_security_group_egress(GroupId=sg.id, IpPermissions=permissions)
    ex.value.response["Error"]["Code"].should.equal(
        "RulesPerSecurityGroupLimitExceeded"
    )
    # verify that we cannot authorize past the limit for a different sec group
    with pytest.raises(ClientError) as ex:
        client.authorize_security_group_egress(
            GroupId=sg.id, IpPermissions=other_permissions
        )
    ex.value.response["Error"]["Code"].should.equal(
        "RulesPerSecurityGroupLimitExceeded"
    )


# Has boto3 equivalent
@mock_ec2_deprecated
def test_sec_group_rule_limit_vpc():
    ec2_conn = boto.connect_ec2()
    vpc_conn = boto.connect_vpc()

    vpc = vpc_conn.create_vpc("10.0.0.0/16")

    sg = ec2_conn.create_security_group("test", "test", vpc_id=vpc.id)
    other_sg = ec2_conn.create_security_group("test_2", "test", vpc_id=vpc.id)

    # INGRESS
    with pytest.raises(EC2ResponseError) as cm:
        ec2_conn.authorize_security_group(
            group_id=sg.id,
            ip_protocol="-1",
            cidr_ip=["{0}.0.0.0/0".format(i) for i in range(110)],
        )
    cm.value.error_code.should.equal("RulesPerSecurityGroupLimitExceeded")

    sg.rules.should.be.empty
    # authorize a rule targeting a different sec group (because this count too)
    success = ec2_conn.authorize_security_group(
        group_id=sg.id, ip_protocol="-1", src_security_group_group_id=other_sg.id
    )
    success.should.be.true
    # fill the rules up the limit
    success = ec2_conn.authorize_security_group(
        group_id=sg.id,
        ip_protocol="-1",
        cidr_ip=["{0}.0.0.0/0".format(i) for i in range(59)],
    )
    # verify that we cannot authorize past the limit for a CIDR IP
    success.should.be.true
    with pytest.raises(EC2ResponseError) as cm:
        ec2_conn.authorize_security_group(
            group_id=sg.id, ip_protocol="-1", cidr_ip=["100.0.0.0/0"]
        )
    cm.value.error_code.should.equal("RulesPerSecurityGroupLimitExceeded")
    # verify that we cannot authorize past the limit for a different sec group
    with pytest.raises(EC2ResponseError) as cm:
        ec2_conn.authorize_security_group(
            group_id=sg.id, ip_protocol="-1", src_security_group_group_id=other_sg.id
        )
    cm.value.error_code.should.equal("RulesPerSecurityGroupLimitExceeded")

    # EGRESS
    # authorize a rule targeting a different sec group (because this count too)
    ec2_conn.authorize_security_group_egress(
        group_id=sg.id, ip_protocol="-1", src_group_id=other_sg.id
    )
    # fill the rules up the limit
    # remember that by default, when created a sec group contains 1 egress rule
    # so our other_sg rule + 48 CIDR IP rules + 1 by default == 50 the limit
    for i in range(1, 59):
        ec2_conn.authorize_security_group_egress(
            group_id=sg.id, ip_protocol="-1", cidr_ip="{0}.0.0.0/0".format(i)
        )
    # verify that we cannot authorize past the limit for a CIDR IP
    with pytest.raises(EC2ResponseError) as cm:
        ec2_conn.authorize_security_group_egress(
            group_id=sg.id, ip_protocol="-1", cidr_ip="50.0.0.0/0"
        )
    cm.value.error_code.should.equal("RulesPerSecurityGroupLimitExceeded")
    # verify that we cannot authorize past the limit for a different sec group
    with pytest.raises(EC2ResponseError) as cm:
        ec2_conn.authorize_security_group_egress(
            group_id=sg.id, ip_protocol="-1", src_group_id=other_sg.id
        )
    cm.value.error_code.should.equal("RulesPerSecurityGroupLimitExceeded")


"""
Boto3
"""


@mock_ec2
def test_add_same_rule_twice_throws_error():
    ec2 = boto3.resource("ec2", region_name="us-west-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    sg = ec2.create_security_group(
        GroupName="sg1", Description="Test security group sg1", VpcId=vpc.id
    )

    # Ingress
    ip_permissions = [
        {
            "IpProtocol": "tcp",
            "FromPort": 27017,
            "ToPort": 27017,
            "IpRanges": [{"CidrIp": "1.2.3.4/32"}],
        }
    ]
    sg.authorize_ingress(IpPermissions=ip_permissions)

    with pytest.raises(ClientError) as ex:
        sg.authorize_ingress(IpPermissions=ip_permissions)
    ex.value.response["Error"]["Code"].should.equal("InvalidPermission.Duplicate")
    ex.value.response["Error"]["Message"].should.match(
        r"^.* specified rule.*already exists$"
    )

    # Egress
    ip_permissions = [
        {
            "IpProtocol": "-1",
            "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
            "Ipv6Ranges": [],
            "PrefixListIds": [],
            "UserIdGroupPairs": [],
        }
    ]

    with pytest.raises(ClientError) as ex:
        sg.authorize_egress(IpPermissions=ip_permissions)
    ex.value.response["Error"]["Code"].should.equal("InvalidPermission.Duplicate")
    ex.value.response["Error"]["Message"].should.match(
        r"^.* specified rule.*already exists$"
    )


@mock_ec2
def test_description_in_ip_permissions():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    conn = boto3.client("ec2", region_name="us-east-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    sg = conn.create_security_group(
        GroupName="sg1", Description="Test security group sg1", VpcId=vpc.id
    )

    ip_permissions = [
        {
            "IpProtocol": "tcp",
            "FromPort": 27017,
            "ToPort": 27017,
            "IpRanges": [{"CidrIp": "1.2.3.4/32", "Description": "testDescription"}],
        }
    ]
    conn.authorize_security_group_ingress(
        GroupId=sg["GroupId"], IpPermissions=ip_permissions
    )

    result = conn.describe_security_groups(GroupIds=[sg["GroupId"]])
    group = result["SecurityGroups"][0]

    assert group["IpPermissions"][0]["IpRanges"][0]["Description"] == "testDescription"
    assert group["IpPermissions"][0]["IpRanges"][0]["CidrIp"] == "1.2.3.4/32"

    sg = conn.create_security_group(
        GroupName="sg2", Description="Test security group sg1", VpcId=vpc.id
    )

    ip_permissions = [
        {
            "IpProtocol": "tcp",
            "FromPort": 27017,
            "ToPort": 27017,
            "IpRanges": [{"CidrIp": "1.2.3.4/32"}],
        }
    ]
    conn.authorize_security_group_ingress(
        GroupId=sg["GroupId"], IpPermissions=ip_permissions
    )

    result = conn.describe_security_groups(GroupIds=[sg["GroupId"]])
    group = result["SecurityGroups"][0]

    assert group["IpPermissions"][0]["IpRanges"][0].get("Description") is None
    assert group["IpPermissions"][0]["IpRanges"][0]["CidrIp"] == "1.2.3.4/32"


@mock_ec2
def test_security_group_tagging_boto3():
    conn = boto3.client("ec2", region_name="us-east-1")

    sg = conn.create_security_group(GroupName=str(uuid4()), Description="Test SG")

    with pytest.raises(ClientError) as ex:
        conn.create_tags(
            Resources=[sg["GroupId"]],
            Tags=[{"Key": "Test", "Value": "Tag"}],
            DryRun=True,
        )
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the CreateTags operation: Request would have succeeded, but DryRun flag is set"
    )

    tag_val = str(uuid4())
    conn.create_tags(
        Resources=[sg["GroupId"]], Tags=[{"Key": "Test", "Value": tag_val}]
    )
    describe = conn.describe_security_groups(
        Filters=[{"Name": "tag-value", "Values": [tag_val]}]
    )
    tag = describe["SecurityGroups"][0]["Tags"][0]
    tag["Value"].should.equal(tag_val)
    tag["Key"].should.equal("Test")


@mock_ec2
def test_security_group_wildcard_tag_filter_boto3():
    conn = boto3.client("ec2", region_name="us-east-1")
    sg = conn.create_security_group(GroupName=str(uuid4()), Description="Test SG")

    rand_name = str(uuid4())[0:6]
    tag_val = f"random {rand_name} things"
    conn.create_tags(
        Resources=[sg["GroupId"]], Tags=[{"Key": "Test", "Value": tag_val}]
    )
    describe = conn.describe_security_groups(
        Filters=[{"Name": "tag-value", "Values": [f"*{rand_name}*"]}]
    )

    tag = describe["SecurityGroups"][0]["Tags"][0]
    tag["Value"].should.equal(tag_val)
    tag["Key"].should.equal("Test")


@mock_ec2
def test_security_group_filter_ip_permission():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")

    conn = boto3.client("ec2", region_name="us-east-1")
    sg_name = str(uuid4())[0:6]
    sg = ec2.create_security_group(
        GroupName=sg_name, Description="Test SG", VpcId=vpc.id
    )

    from_port = randint(0, 65535)
    to_port = randint(0, 65535)
    ip_permissions = [
        {
            "IpProtocol": "tcp",
            "FromPort": from_port,
            "ToPort": to_port,
            "IpRanges": [],
        },
    ]

    sg.authorize_ingress(IpPermissions=ip_permissions)

    filters = [{"Name": "ip-permission.from-port", "Values": [f"{from_port}"]}]
    describe = retrieve_all_sgs(conn, filters)
    describe.should.have.length_of(1)

    describe[0]["GroupName"].should.equal(sg_name)


def retrieve_all_sgs(conn, filters=[]):
    res = conn.describe_security_groups(Filters=filters)
    all_groups = res["SecurityGroups"]
    next_token = res.get("NextToken")
    while next_token:
        res = conn.describe_security_groups(Filters=filters)
        all_groups.extend(res["SecurityGroups"])
        next_token = res.get("NextToken")
    return all_groups


@mock_ec2
def test_authorize_and_revoke_in_bulk():
    ec2 = boto3.resource("ec2", region_name="us-west-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")

    sg01 = ec2.create_security_group(
        GroupName=str(uuid4()), Description="Test sg01", VpcId=vpc.id
    )
    sg02 = ec2.create_security_group(
        GroupName=str(uuid4()), Description="Test sg02", VpcId=vpc.id
    )
    sg03 = ec2.create_security_group(GroupName=str(uuid4()), Description="Test sg03")
    sg04 = ec2.create_security_group(GroupName=str(uuid4()), Description="Test sg04")
    ip_permissions = [
        {
            "IpProtocol": "tcp",
            "FromPort": 27017,
            "ToPort": 27017,
            "UserIdGroupPairs": [{"GroupId": sg02.id, "UserId": sg02.owner_id}],
            "IpRanges": [],
            "Ipv6Ranges": [],
            "PrefixListIds": [],
        },
        {
            "IpProtocol": "tcp",
            "FromPort": 27018,
            "ToPort": 27018,
            "UserIdGroupPairs": [{"GroupId": sg02.id, "UserId": sg02.owner_id}],
            "IpRanges": [],
            "Ipv6Ranges": [],
            "PrefixListIds": [],
        },
        {
            "IpProtocol": "tcp",
            "FromPort": 27017,
            "ToPort": 27017,
            "UserIdGroupPairs": [{"GroupId": sg03.id, "UserId": sg03.owner_id}],
            "IpRanges": [],
            "Ipv6Ranges": [],
            "PrefixListIds": [],
        },
        {
            "IpProtocol": "tcp",
            "FromPort": 27015,
            "ToPort": 27015,
            "UserIdGroupPairs": [{"GroupId": sg04.id, "UserId": sg04.owner_id}],
            "IpRanges": [
                {"CidrIp": "10.10.10.0/24", "Description": "Some Description"}
            ],
            "Ipv6Ranges": [],
            "PrefixListIds": [],
        },
        {
            "IpProtocol": "tcp",
            "FromPort": 27016,
            "ToPort": 27016,
            "UserIdGroupPairs": [{"GroupId": sg04.id, "UserId": sg04.owner_id}],
            "IpRanges": [{"CidrIp": "10.10.10.0/24"}],
            "Ipv6Ranges": [],
            "PrefixListIds": [],
        },
    ]

    org_ip_permissions = copy.deepcopy(ip_permissions)

    for rule in ip_permissions.copy():
        for other_rule in ip_permissions.copy():
            if (
                rule is not other_rule
                and rule.get("IpProtocol") == other_rule.get("IpProtocol")
                and rule.get("FromPort") == other_rule.get("FromPort")
                and rule.get("ToPort") == other_rule.get("ToPort")
            ):
                if rule in ip_permissions:
                    ip_permissions.remove(rule)
                if other_rule in ip_permissions:
                    ip_permissions.remove(other_rule)

                rule["UserIdGroupPairs"].extend(
                    [
                        item
                        for item in other_rule["UserIdGroupPairs"]
                        if item not in rule["UserIdGroupPairs"]
                    ]
                )
                rule["IpRanges"].extend(
                    [
                        item
                        for item in other_rule["IpRanges"]
                        if item not in rule["IpRanges"]
                    ]
                )
                rule["Ipv6Ranges"].extend(
                    [
                        item
                        for item in other_rule["Ipv6Ranges"]
                        if item not in rule["Ipv6Ranges"]
                    ]
                )
                rule["PrefixListIds"].extend(
                    [
                        item
                        for item in other_rule["PrefixListIds"]
                        if item not in rule["PrefixListIds"]
                    ]
                )
                if rule not in ip_permissions:
                    ip_permissions.append(json.loads(json.dumps(rule, sort_keys=True)))

    expected_ip_permissions = copy.deepcopy(ip_permissions)
    expected_ip_permissions[1]["UserIdGroupPairs"][0]["GroupId"] = sg04.id
    expected_ip_permissions[3]["UserIdGroupPairs"][0]["GroupId"] = sg03.id
    expected_ip_permissions = json.dumps(expected_ip_permissions, sort_keys=True)

    sg01.authorize_ingress(IpPermissions=org_ip_permissions)
    # Due to drift property of the Security Group,
    # rules with same Ip protocol, FromPort and ToPort will be merged together
    sg01.ip_permissions.should.have.length_of(4)
    sorted_sg01_ip_permissions = json.dumps(sg01.ip_permissions, sort_keys=True)
    for ip_permission in expected_ip_permissions:
        sorted_sg01_ip_permissions.should.contain(ip_permission)

    sg01.revoke_ingress(IpPermissions=ip_permissions)
    sg01.ip_permissions.should.be.empty
    for ip_permission in expected_ip_permissions:
        sg01.ip_permissions.shouldnt.contain(ip_permission)

    sg01.authorize_egress(IpPermissions=org_ip_permissions)
    # Due to drift property of the Security Group,
    # rules with same Ip protocol, FromPort and ToPort will be merged together
    sg01.ip_permissions_egress.should.have.length_of(5)
    sorted_sg01_ip_permissions_egress = json.dumps(
        sg01.ip_permissions_egress, sort_keys=True
    )
    for ip_permission in expected_ip_permissions:
        sorted_sg01_ip_permissions_egress.should.contain(ip_permission)

    sg01.revoke_egress(IpPermissions=ip_permissions)
    sg01.ip_permissions_egress.should.have.length_of(1)
    for ip_permission in expected_ip_permissions:
        sg01.ip_permissions_egress.shouldnt.contain(ip_permission)


@mock_ec2
def test_security_group_ingress_without_multirule():
    ec2 = boto3.resource("ec2", "ca-central-1")
    sg = ec2.create_security_group(Description="Test SG", GroupName=str(uuid4()))

    assert len(sg.ip_permissions) == 0
    sg.authorize_ingress(
        CidrIp="192.168.0.1/32", FromPort=22, ToPort=22, IpProtocol="tcp"
    )

    # Fails
    assert len(sg.ip_permissions) == 1


@mock_ec2
def test_security_group_ingress_without_multirule_after_reload():
    ec2 = boto3.resource("ec2", "ca-central-1")
    sg = ec2.create_security_group(Description="Test SG", GroupName=str(uuid4()))

    assert len(sg.ip_permissions) == 0
    sg.authorize_ingress(
        CidrIp="192.168.0.1/32", FromPort=22, ToPort=22, IpProtocol="tcp"
    )

    # Also Fails
    sg_after = ec2.SecurityGroup(sg.id)
    assert len(sg_after.ip_permissions) == 1


# Has boto3 equivalent
@mock_ec2_deprecated
def test_get_all_security_groups_filter_with_same_vpc_id():
    conn = boto.connect_ec2("the_key", "the_secret")
    vpc_id = "vpc-5300000c"
    security_group = conn.create_security_group("test1", "test1", vpc_id=vpc_id)
    security_group2 = conn.create_security_group("test2", "test2", vpc_id=vpc_id)

    security_group.vpc_id.should.equal(vpc_id)
    security_group2.vpc_id.should.equal(vpc_id)

    security_groups = conn.get_all_security_groups(
        group_ids=[security_group.id], filters={"vpc-id": [vpc_id]}
    )
    security_groups.should.have.length_of(1)

    with pytest.raises(EC2ResponseError) as cm:
        conn.get_all_security_groups(group_ids=["does_not_exist"])
    cm.value.code.should.equal("InvalidGroup.NotFound")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none


@mock_ec2
def test_get_all_security_groups_filter_with_same_vpc_id_boto3():
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    client = boto3.client("ec2", region_name="us-east-1")
    vpc_id = "vpc-5300000c"
    security_group = ec2.create_security_group(
        GroupName=str(uuid4()), Description="test1", VpcId=vpc_id
    )
    security_group2 = ec2.create_security_group(
        GroupName=str(uuid4()), Description="test2", VpcId=vpc_id
    )

    security_group.vpc_id.should.equal(vpc_id)
    security_group2.vpc_id.should.equal(vpc_id)

    security_groups = client.describe_security_groups(
        GroupIds=[security_group.id], Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
    )["SecurityGroups"]
    security_groups.should.have.length_of(1)

    with pytest.raises(ClientError) as ex:
        client.describe_security_groups(GroupIds=["does_not_exist"])
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["ResponseMetadata"].should.have.key("RequestId")
    ex.value.response["Error"]["Code"].should.equal("InvalidGroup.NotFound")


@mock_ec2
def test_revoke_security_group_egress():
    ec2 = boto3.resource("ec2", "us-east-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    sg = ec2.create_security_group(
        Description="Test SG", GroupName=str(uuid4()), VpcId=vpc.id
    )

    sg.ip_permissions_egress.should.equal(
        [
            {
                "IpProtocol": "-1",
                "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                "UserIdGroupPairs": [],
                "Ipv6Ranges": [],
                "PrefixListIds": [],
            }
        ]
    )

    sg.revoke_egress(
        IpPermissions=[
            {
                "IpProtocol": "-1",
                "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                "UserIdGroupPairs": [],
                "Ipv6Ranges": [],
                "PrefixListIds": [],
            }
        ]
    )

    sg.reload()
    sg.ip_permissions_egress.should.have.length_of(0)


@mock_ec2
def test_update_security_group_rule_descriptions_egress():
    ec2 = boto3.resource("ec2", "us-east-1")
    client = boto3.client("ec2", "us-east-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    sg_name = str(uuid4())
    sg = ec2.create_security_group(
        Description="Test SG", GroupName=sg_name, VpcId=vpc.id
    )
    sg_id = sg.id

    ip_ranges = client.describe_security_groups(GroupIds=[sg_id])["SecurityGroups"][0][
        "IpPermissionsEgress"
    ][0]["IpRanges"]
    ip_ranges.should.have.length_of(1)
    ip_ranges[0].should.equal({"CidrIp": "0.0.0.0/0"})

    client.update_security_group_rule_descriptions_egress(
        GroupName=sg_name,
        IpPermissions=[
            {
                "IpProtocol": "-1",
                "IpRanges": [{"CidrIp": "0.0.0.0/0", "Description": "my d3scription"}],
                "UserIdGroupPairs": [],
                "Ipv6Ranges": [],
                "PrefixListIds": [],
            }
        ],
    )

    ip_ranges = client.describe_security_groups(GroupIds=[sg_id])["SecurityGroups"][0][
        "IpPermissionsEgress"
    ][0]["IpRanges"]
    ip_ranges.should.have.length_of(1)
    ip_ranges[0].should.equal({"CidrIp": "0.0.0.0/0", "Description": "my d3scription"})


@mock_ec2
def test_update_security_group_rule_descriptions_ingress():
    ec2 = boto3.resource("ec2", "us-east-1")
    client = boto3.client("ec2", "us-east-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    sg_name = str(uuid4())
    sg = ec2.create_security_group(
        Description="Test SG", GroupName=sg_name, VpcId=vpc.id
    )
    sg_id = sg.id

    ip_permissions = [
        {
            "IpProtocol": "tcp",
            "FromPort": 27017,
            "ToPort": 27017,
            "IpRanges": [{"CidrIp": "1.2.3.4/32", "Description": "first desc"}],
        }
    ]
    client.authorize_security_group_ingress(GroupId=sg_id, IpPermissions=ip_permissions)

    ip_ranges = client.describe_security_groups(GroupIds=[sg_id])["SecurityGroups"][0][
        "IpPermissions"
    ][0]["IpRanges"]
    ip_ranges.should.have.length_of(1)
    ip_ranges[0].should.equal({"CidrIp": "1.2.3.4/32", "Description": "first desc"})

    client.update_security_group_rule_descriptions_ingress(
        GroupName=sg_name,
        IpPermissions=[
            {
                "IpProtocol": "tcp",
                "FromPort": 27017,
                "ToPort": 27017,
                "IpRanges": [{"CidrIp": "1.2.3.4/32", "Description": "second desc"}],
            }
        ],
    )

    ip_ranges = client.describe_security_groups(GroupIds=[sg_id])["SecurityGroups"][0][
        "IpPermissions"
    ][0]["IpRanges"]
    ip_ranges.should.have.length_of(1)
    ip_ranges[0].should.equal({"CidrIp": "1.2.3.4/32", "Description": "second desc"})


@mock_ec2
def test_non_existent_security_group_raises_error_on_authorize():
    client = boto3.client("ec2", "us-east-1")
    non_existent_sg = "sg-123abc"
    expected_error = "The security group '{}' does not exist".format(non_existent_sg)
    authorize_funcs = [
        client.authorize_security_group_egress,
        client.authorize_security_group_ingress,
    ]
    for authorize_func in authorize_funcs:
        with pytest.raises(ClientError) as ex:
            authorize_func(GroupId=non_existent_sg, IpPermissions=[{}])
        ex.value.response["Error"]["Code"].should.equal("InvalidGroup.NotFound")
        ex.value.response["Error"]["Message"].should.equal(expected_error)


@mock_ec2
def test_security_group_rules_added_via_the_backend_can_be_revoked_via_the_api():
    if settings.TEST_SERVER_MODE:
        raise unittest.SkipTest("Can't test backend directly in server mode.")
    ec2_resource = boto3.resource("ec2", region_name="us-east-1")
    ec2_client = boto3.client("ec2", region_name="us-east-1")
    vpc = ec2_resource.create_vpc(CidrBlock="10.0.0.0/16")
    group_name = str(uuid4())
    sg = ec2_resource.create_security_group(
        GroupName=group_name, Description="test", VpcId=vpc.id
    )
    # Add an ingress/egress rule using the EC2 backend directly.
    rule_ingress = {
        "group_name_or_id": sg.id,
        "from_port": 0,
        "ip_protocol": "udp",
        "ip_ranges": [],
        "to_port": 65535,
        "source_groups": [{"GroupId": sg.id}],
    }
    ec2_backend.authorize_security_group_ingress(**rule_ingress)
    rule_egress = {
        "group_name_or_id": sg.id,
        "from_port": 8443,
        "ip_protocol": "tcp",
        "ip_ranges": [],
        "to_port": 8443,
        "source_groups": [{"GroupId": sg.id}],
    }
    ec2_backend.authorize_security_group_egress(**rule_egress)
    # Both rules (plus the default egress) should now be present.
    sg = ec2_client.describe_security_groups(
        Filters=[{"Name": "group-name", "Values": [group_name]}]
    ).get("SecurityGroups")[0]
    assert len(sg["IpPermissions"]) == 1
    assert len(sg["IpPermissionsEgress"]) == 2
    # Revoking via the API should work for all rules (even those we added directly).
    ec2_client.revoke_security_group_egress(
        GroupId=sg["GroupId"], IpPermissions=sg["IpPermissionsEgress"]
    )
    ec2_client.revoke_security_group_ingress(
        GroupId=sg["GroupId"], IpPermissions=sg["IpPermissions"]
    )
    sg = ec2_client.describe_security_groups(
        Filters=[{"Name": "group-name", "Values": [group_name]}]
    ).get("SecurityGroups")[0]
    assert len(sg["IpPermissions"]) == 0
    assert len(sg["IpPermissionsEgress"]) == 0


@mock_ec2
def test_filter_description():
    ec2r = boto3.resource("ec2", region_name="us-west-1")
    vpc = ec2r.create_vpc(CidrBlock="10.250.0.0/16")

    unique = str(uuid4())
    sg1 = vpc.create_security_group(
        Description=(f"A {unique} Description"), GroupName="test-1"
    )
    sg2 = vpc.create_security_group(
        Description="Another Description That Awes The Human Mind", GroupName="test-2"
    )

    filter_to_match_group_1_description = {
        "Name": "description",
        "Values": [unique],
    }

    security_groups = ec2r.security_groups.filter(
        Filters=[filter_to_match_group_1_description]
    )

    security_groups = list(security_groups)
    assert len(security_groups) == 1
    assert security_groups[0].group_id == sg1.group_id


@mock_ec2
def test_filter_egress__ip_permission__cidr():
    if settings.TEST_SERVER_MODE:
        raise SkipTest(
            "CIDR's might already exist due to other tests creating IP ranges"
        )
    ec2r = boto3.resource("ec2", region_name="us-west-1")
    vpc = ec2r.create_vpc(CidrBlock="10.250.1.0/16")

    sg1 = vpc.create_security_group(
        Description="A Described Description Descriptor", GroupName="test-1"
    )
    sg2 = vpc.create_security_group(
        Description="Another Description That Awes The Human Mind", GroupName="test-2"
    )

    sg1.authorize_egress(
        IpPermissions=[
            {
                "FromPort": 7357,
                "ToPort": 7357,
                "IpProtocol": "tcp",
                "IpRanges": [{"CidrIp": "10.250.0.0/16"}, {"CidrIp": "10.251.0.0/16"}],
            }
        ]
    )
    sg2.authorize_egress(
        IpPermissions=[
            {
                "FromPort": 7357,
                "ToPort": 7357,
                "IpProtocol": "tcp",
                "IpRanges": [{"CidrIp": "172.16.0.0/16"}, {"CidrIp": "172.17.0.0/16"}],
            }
        ]
    )
    filter_to_match_group_1 = {
        "Name": "egress.ip-permission.cidr",
        "Values": ["10.250.0.0/16"],
    }
    security_groups = ec2r.security_groups.filter(Filters=[filter_to_match_group_1])

    security_groups = list(security_groups)
    assert len(security_groups) == 1
    assert security_groups[0].group_id == sg1.group_id


@mock_ec2
def test_filter_egress__ip_permission__from_port():
    ec2r = boto3.resource("ec2", region_name="us-west-1")
    vpc = ec2r.create_vpc(CidrBlock="10.250.1.0/16")

    sg1 = vpc.create_security_group(
        Description="A Described Description Descriptor", GroupName="test-1"
    )
    sg2 = vpc.create_security_group(
        Description="Another Description That Awes The Human Mind", GroupName="test-2"
    )

    from_port = randint(9999, 59999)
    sg1.authorize_egress(
        IpPermissions=[
            {
                "FromPort": from_port,
                "ToPort": 7359,
                "IpProtocol": "tcp",
                "IpRanges": [{"CidrIp": "10.250.0.0/16"}, {"CidrIp": "10.251.0.0/16"}],
            }
        ]
    )
    sg2.authorize_egress(
        IpPermissions=[
            {
                "FromPort": 8000,
                "ToPort": 8020,
                "IpProtocol": "tcp",
                "IpRanges": [{"CidrIp": "172.16.0.0/16"}, {"CidrIp": "172.17.0.0/16"}],
            }
        ]
    )
    filter_to_match_group_1 = {
        "Name": "egress.ip-permission.from-port",
        "Values": [f"{from_port}"],
    }
    security_groups = ec2r.security_groups.filter(Filters=[filter_to_match_group_1])

    security_groups = list(security_groups)
    [s.group_id for s in security_groups].should.contain(sg1.group_id)
    [s.group_id for s in security_groups].shouldnt.contain(sg2.group_id)


@mock_ec2
def test_filter_egress__ip_permission__group_id():
    ec2r = boto3.resource("ec2", region_name="us-west-1")
    vpc = ec2r.create_vpc(CidrBlock="10.250.1.0/16")

    sg1 = vpc.create_security_group(
        Description="A Described Description Descriptor", GroupName="test-1"
    )
    sg2 = vpc.create_security_group(
        Description="Another Description That Awes The Human Mind", GroupName="test-2"
    )
    sg3 = vpc.create_security_group(
        Description="Yet Another Descriptive Description", GroupName="test-3"
    )
    sg4 = vpc.create_security_group(
        Description="Such Description Much Described", GroupName="test-4"
    )

    sg1.authorize_egress(
        IpPermissions=[
            {
                "FromPort": 7357,
                "ToPort": 7359,
                "IpProtocol": "tcp",
                "UserIdGroupPairs": [{"GroupId": sg3.group_id}],
            }
        ]
    )
    sg2.authorize_egress(
        IpPermissions=[
            {
                "FromPort": 8000,
                "ToPort": 8020,
                "IpProtocol": "tcp",
                "UserIdGroupPairs": [{"GroupId": sg4.group_id}],
            }
        ]
    )

    filter_to_match_group_1 = {
        "Name": "egress.ip-permission.group-id",
        "Values": [sg3.group_id],
    }
    security_groups = ec2r.security_groups.filter(Filters=[filter_to_match_group_1])

    security_groups = list(security_groups)
    assert len(security_groups) == 1
    assert security_groups[0].group_id == sg1.group_id


@mock_ec2
def test_filter_egress__ip_permission__group_name_create_with_id_filter_by_name():
    """
    this fails to find the group in the AWS API, so we should also fail to find it
    """
    ec2r = boto3.resource("ec2", region_name="us-west-1")
    vpc = ec2r.create_vpc(CidrBlock="10.250.1.0/16")

    sg1 = vpc.create_security_group(
        Description="A Described Description Descriptor", GroupName="test-1"
    )
    sg2 = vpc.create_security_group(
        Description="Another Description That Awes The Human Mind", GroupName="test-2"
    )
    sg3 = vpc.create_security_group(
        Description="Yet Another Descriptive Description", GroupName="test-3"
    )
    sg4 = vpc.create_security_group(
        Description="Such Description Much Described", GroupName="test-4"
    )

    sg1.authorize_egress(
        IpPermissions=[
            {
                "FromPort": 7357,
                "ToPort": 7359,
                "IpProtocol": "tcp",
                "UserIdGroupPairs": [{"GroupId": sg3.group_id}],
            }
        ]
    )
    sg2.authorize_egress(
        IpPermissions=[
            {
                "FromPort": 8000,
                "ToPort": 8020,
                "IpProtocol": "tcp",
                "UserIdGroupPairs": [{"GroupId": sg4.group_id}],
            }
        ]
    )

    filter_to_match_group_1 = {
        "Name": "egress.ip-permission.group-name",
        "Values": [sg3.group_name],
    }
    sg1.load()
    sg2.load()

    security_groups = ec2r.security_groups.filter(Filters=[filter_to_match_group_1])

    security_groups = list(security_groups)
    assert len(security_groups) == 0


@mock_ec2
def test_filter_egress__ip_permission__group_name_create_with_id_filter_by_id():
    ec2r = boto3.resource("ec2", region_name="us-west-1")
    vpc = ec2r.create_vpc(CidrBlock="10.250.1.0/16")

    sg1 = vpc.create_security_group(
        Description="A Described Description Descriptor", GroupName="test-1"
    )
    sg2 = vpc.create_security_group(
        Description="Another Description That Awes The Human Mind", GroupName="test-2"
    )
    sg3 = vpc.create_security_group(
        Description="Yet Another Descriptive Description", GroupName="test-3"
    )
    sg4 = vpc.create_security_group(
        Description="Such Description Much Described", GroupName="test-4"
    )

    sg1.authorize_egress(
        IpPermissions=[
            {
                "FromPort": 7357,
                "ToPort": 7359,
                "IpProtocol": "tcp",
                "UserIdGroupPairs": [{"GroupId": sg3.group_id}],
            }
        ]
    )
    sg2.authorize_egress(
        IpPermissions=[
            {
                "FromPort": 8000,
                "ToPort": 8020,
                "IpProtocol": "tcp",
                "UserIdGroupPairs": [{"GroupId": sg4.group_id}],
            }
        ]
    )

    filter_to_match_group_1 = {
        "Name": "egress.ip-permission.group-id",
        "Values": [sg3.group_id],
    }
    sg1.load()
    sg2.load()

    security_groups = ec2r.security_groups.filter(Filters=[filter_to_match_group_1])

    security_groups = list(security_groups)
    assert len(security_groups) == 1
    assert security_groups[0].group_id == sg1.group_id


@mock_ec2
def test_filter_egress__ip_permission__protocol():
    ec2r = boto3.resource("ec2", region_name="us-west-1")
    vpc = ec2r.create_vpc(CidrBlock="10.250.1.0/16")

    sg1 = vpc.create_security_group(
        Description="A Described Description Descriptor", GroupName="test-1"
    )
    sg2 = vpc.create_security_group(
        Description="Another Description That Awes The Human Mind", GroupName="test-2"
    )

    sg1.authorize_egress(
        IpPermissions=[
            {
                "FromPort": 7357,
                "ToPort": 7359,
                "IpProtocol": "tcp",
                "IpRanges": [{"CidrIp": "10.250.0.0/16"}, {"CidrIp": "10.251.0.0/16"}],
            }
        ]
    )
    sg2.authorize_egress(
        IpPermissions=[
            {
                "FromPort": 7357,
                "ToPort": 7359,
                "IpProtocol": "udp",
                "IpRanges": [{"CidrIp": "10.250.0.0/16"}, {"CidrIp": "10.251.0.0/16"}],
            }
        ]
    )
    filter_to_match_group_1 = {
        "Name": "egress.ip-permission.protocol",
        "Values": ["tcp"],
    }
    security_groups = ec2r.security_groups.filter(Filters=[filter_to_match_group_1])

    group_ids = [sg.group_id for sg in security_groups]
    group_ids.should.contain(sg1.group_id)
    group_ids.shouldnt.contain(sg2.group_id)


@mock_ec2
def test_filter_egress__ip_permission__to_port():
    ec2r = boto3.resource("ec2", region_name="us-west-1")
    vpc = ec2r.create_vpc(CidrBlock="10.250.1.0/16")

    sg1 = vpc.create_security_group(
        Description="A Described Description Descriptor", GroupName="test-1"
    )
    sg2 = vpc.create_security_group(
        Description="Another Description That Awes The Human Mind", GroupName="test-2"
    )

    to_port = randint(9999, 59999)
    sg1.authorize_egress(
        IpPermissions=[
            {
                "FromPort": 7357,
                "ToPort": to_port,
                "IpProtocol": "tcp",
                "IpRanges": [{"CidrIp": "10.250.0.0/16"}, {"CidrIp": "10.251.0.0/16"}],
            }
        ]
    )
    sg2.authorize_egress(
        IpPermissions=[
            {
                "FromPort": 7357,
                "ToPort": 7360,
                "IpProtocol": "tcp",
                "IpRanges": [{"CidrIp": "172.16.0.0/16"}, {"CidrIp": "172.17.0.0/16"}],
            }
        ]
    )
    filter_to_match_group_1 = {
        "Name": "egress.ip-permission.to-port",
        "Values": [f"{to_port}"],
    }
    security_groups = ec2r.security_groups.filter(Filters=[filter_to_match_group_1])

    security_groups = list(security_groups)
    [s.group_id for s in security_groups].should.contain(sg1.group_id)
    [s.group_id for s in security_groups].shouldnt.contain(sg2.group_id)


@mock_ec2
def test_get_groups_by_ippermissions_group_id_filter():
    ec2r = boto3.resource("ec2", region_name="us-west-1")
    vpc = ec2r.create_vpc(CidrBlock="10.250.0.0/16")
    sg1 = vpc.create_security_group(Description="test", GroupName="test-1")
    sg2 = vpc.create_security_group(Description="test", GroupName="test-2")

    sg1_allows_sg2_ingress_rule = {
        "IpProtocol": "tcp",
        "FromPort": 31337,
        "ToPort": 31337,
        "UserIdGroupPairs": [{"GroupId": sg2.group_id, "VpcId": sg2.vpc_id}],
    }
    sg1.authorize_ingress(IpPermissions=[sg1_allows_sg2_ingress_rule])

    # we should be able to describe security groups and filter for all the ones that contain
    # a reference to another group ID

    match_only_groups_whose_ingress_rules_refer_to_group_2 = {
        "Name": "ip-permission.group-id",
        "Values": [sg2.group_id],
    }
    security_groups = ec2r.security_groups.filter(
        Filters=[match_only_groups_whose_ingress_rules_refer_to_group_2]
    )

    security_groups = list(security_groups)
    assert len(security_groups) == 1
    assert security_groups[0].group_id == sg1.group_id


@mock_ec2
def test_get_groups_by_ippermissions_group_id_filter_across_vpcs():
    # setup 2 VPCs, each with a single Security Group
    # where one security group authorizes the other sg (in another vpc) via GroupId
    ec2r = boto3.resource("ec2", region_name="us-west-1")

    vpc1 = ec2r.create_vpc(CidrBlock="10.250.0.0/16")
    vpc2 = ec2r.create_vpc(CidrBlock="10.251.0.0/16")

    sg1 = vpc1.create_security_group(Description="test", GroupName="test-1")
    sg2 = vpc2.create_security_group(Description="test", GroupName="test-2")

    sg1_allows_sg2_ingress_rule = {
        "IpProtocol": "tcp",
        "FromPort": 31337,
        "ToPort": 31337,
        "UserIdGroupPairs": [{"GroupId": sg2.group_id, "VpcId": sg2.vpc_id}],
    }
    sg1.authorize_ingress(IpPermissions=[sg1_allows_sg2_ingress_rule])

    # we should be able to describe security groups and filter for all the ones that contain
    # a reference to another group ID

    match_only_groups_whose_ingress_rules_refer_to_group_2 = {
        "Name": "ip-permission.group-id",
        "Values": [sg2.group_id],
    }
    security_groups = ec2r.security_groups.filter(
        Filters=[match_only_groups_whose_ingress_rules_refer_to_group_2]
    )

    security_groups = list(security_groups)
    assert len(security_groups) == 1
    assert security_groups[0].group_id == sg1.group_id
