import copy
import json
import unittest
from random import randint
from unittest import SkipTest
from uuid import uuid4

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws, settings
from moto.core import DEFAULT_ACCOUNT_ID
from moto.ec2 import ec2_backends

REGION = "us-east-1"


@mock_aws
def test_create_and_describe_security_group():
    ec2 = boto3.resource("ec2", REGION)
    client = boto3.client("ec2", REGION)

    with pytest.raises(ClientError) as ex:
        client.create_security_group(GroupName="test", Description="test", DryRun=True)
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 412
    assert ex.value.response["Error"]["Code"] == "DryRunOperation"
    assert (
        ex.value.response["Error"]["Message"]
        == "An error occurred (DryRunOperation) when calling the CreateSecurityGroup operation: Request would have succeeded, but DryRun flag is set"
    )

    sec_name = str(uuid4())
    security_group = ec2.create_security_group(GroupName=sec_name, Description="test")

    assert security_group.group_name == sec_name
    assert security_group.description == "test"

    # Trying to create another group with the same name should throw an error
    with pytest.raises(ClientError) as ex:
        client.create_security_group(GroupName=sec_name, Description="n/a")
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "InvalidGroup.Duplicate"

    all_groups = retrieve_all_sgs(client)
    # The default group gets created automatically
    assert security_group.id in [g["GroupId"] for g in all_groups]
    group_names = set([group["GroupName"] for group in all_groups])
    assert "default" in group_names
    assert sec_name in group_names


@mock_aws
def test_create_security_group_without_description_raises_error():
    ec2 = boto3.resource("ec2", REGION)

    with pytest.raises(ClientError) as ex:
        ec2.create_security_group(GroupName="test security group", Description="")
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "MissingParameter"


@mock_aws
def test_default_security_group():
    client = boto3.client("ec2", REGION)
    groups = retrieve_all_sgs(client)
    assert "default" in [g["GroupName"] for g in groups]


@mock_aws
def test_create_and_describe_vpc_security_group():
    ec2 = boto3.resource("ec2", REGION)
    client = boto3.client("ec2", REGION)

    name = str(uuid4())
    vpc_id = f"vpc-{str(uuid4())[0:6]}"
    group_with = ec2.create_security_group(
        GroupName=name, Description="test", VpcId=vpc_id
    )

    assert group_with.vpc_id == vpc_id

    assert group_with.group_name == name
    assert group_with.description == "test"

    # Trying to create another group with the same name in the same VPC should
    # throw an error
    with pytest.raises(ClientError) as ex:
        ec2.create_security_group(GroupName=name, Description="n/a", VpcId=vpc_id)
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "InvalidGroup.Duplicate"

    # Trying to create another group in the same name without VPC should pass
    group_without = ec2.create_security_group(
        GroupName=name, Description="non-vpc-group"
    )

    all_groups = retrieve_all_sgs(client)
    assert group_with.id in [a["GroupId"] for a in all_groups]
    assert group_without.id in [a["GroupId"] for a in all_groups]

    all_groups = client.describe_security_groups(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
    )["SecurityGroups"]

    assert len(all_groups) == 1
    assert all_groups[0]["VpcId"] == vpc_id
    assert all_groups[0]["GroupName"] == name


@mock_aws
def test_create_two_security_groups_with_same_name_in_different_vpc():
    ec2 = boto3.resource("ec2", REGION)
    client = boto3.client("ec2", REGION)

    name = str(uuid4())
    vpc_id = "vpc-5300000c"
    vpc_id2 = "vpc-5300000d"

    sg1 = ec2.create_security_group(GroupName=name, Description="n/a 1", VpcId=vpc_id)
    sg2 = ec2.create_security_group(GroupName=name, Description="n/a 2", VpcId=vpc_id2)

    all_groups = retrieve_all_sgs(client)
    group_ids = [group["GroupId"] for group in all_groups]
    assert sg1.id in group_ids
    assert sg2.id in group_ids

    group_names = [group["GroupName"] for group in all_groups]
    assert name in group_names


@mock_aws
def test_create_two_security_groups_in_vpc_with_ipv6_enabled():
    ec2 = boto3.resource("ec2", region_name=REGION)
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16", AmazonProvidedIpv6CidrBlock=True)

    security_group = ec2.create_security_group(
        GroupName=str(uuid4()), Description="Test security group sg01", VpcId=vpc.id
    )

    # The security group must have two defaul egress rules (one for ipv4 and aonther for ipv6)
    assert len(security_group.ip_permissions_egress) == 2


@mock_aws
def test_deleting_security_groups():
    ec2 = boto3.resource("ec2", REGION)
    client = boto3.client("ec2", REGION)
    sg_name1 = str(uuid4())
    sg_name2 = str(uuid4())
    group1 = ec2.create_security_group(GroupName=sg_name1, Description="test desc 1")
    group2 = ec2.create_security_group(GroupName=sg_name2, Description="test desc 2")

    all_groups = retrieve_all_sgs(client)
    assert group1.id in [g["GroupId"] for g in all_groups]
    assert group2.id in [g["GroupId"] for g in all_groups]

    # Deleting a group that doesn't exist should throw an error
    with pytest.raises(ClientError) as ex:
        client.delete_security_group(GroupName="foobar")
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "InvalidGroup.NotFound"

    # Delete by name
    with pytest.raises(ClientError) as ex:
        client.delete_security_group(GroupName=sg_name2, DryRun=True)
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 412
    assert ex.value.response["Error"]["Code"] == "DryRunOperation"
    assert (
        ex.value.response["Error"]["Message"]
        == "An error occurred (DryRunOperation) when calling the DeleteSecurityGroup operation: Request would have succeeded, but DryRun flag is set"
    )

    client.delete_security_group(GroupName=sg_name2)

    all_groups = retrieve_all_sgs(client)
    assert group1.id in [g["GroupId"] for g in all_groups]
    assert group2.id not in [g["GroupId"] for g in all_groups]

    # Delete by group id
    client.delete_security_group(GroupId=group1.id)

    all_groups = retrieve_all_sgs(client)
    assert group1.id not in [g["GroupId"] for g in all_groups]


@mock_aws
def test_delete_security_group_in_vpc():
    ec2 = boto3.resource("ec2", REGION)
    client = boto3.client("ec2", REGION)

    group = ec2.create_security_group(
        GroupName=str(uuid4()), Description="test1", VpcId="vpc-12345"
    )

    all_groups = retrieve_all_sgs(client)
    assert group.id in [g["GroupId"] for g in all_groups]

    # this should not throw an exception
    client.delete_security_group(GroupId=group.id)

    all_groups = retrieve_all_sgs(client)
    assert group.id not in [g["GroupId"] for g in all_groups]


@mock_aws
def test_authorize_ip_range_and_revoke():
    ec2 = boto3.resource("ec2", REGION)
    client = boto3.client("ec2", REGION)
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
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 412
    assert ex.value.response["Error"]["Code"] == "DryRunOperation"
    assert (
        ex.value.response["Error"]["Message"]
        == "An error occurred (DryRunOperation) when calling the AuthorizeSecurityGroupIngress operation: Request would have succeeded, but DryRun flag is set"
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

    assert len(security_group.ip_permissions) == 1
    assert security_group.ip_permissions[0]["ToPort"] == 2222
    assert security_group.ip_permissions[0]["IpProtocol"] == "tcp"
    assert security_group.ip_permissions[0]["IpRanges"] == [
        {"CidrIp": "123.123.123.123/32"}
    ]

    # Wrong Cidr should throw error
    with pytest.raises(ClientError) as ex:
        wrong_permissions = copy.deepcopy(ingress_permissions)
        wrong_permissions[0]["IpRanges"][0]["CidrIp"] = "123.123.123.122/32"
        security_group.revoke_ingress(IpPermissions=wrong_permissions)
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "InvalidPermission.NotFound"

    # Actually revoke
    with pytest.raises(ClientError) as ex:
        security_group.revoke_ingress(IpPermissions=ingress_permissions, DryRun=True)
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 412
    assert ex.value.response["Error"]["Code"] == "DryRunOperation"
    assert (
        ex.value.response["Error"]["Message"]
        == "An error occurred (DryRunOperation) when calling the RevokeSecurityGroupIngress operation: Request would have succeeded, but DryRun flag is set"
    )

    security_group.revoke_ingress(IpPermissions=ingress_permissions)

    assert len(security_group.ip_permissions) == 0

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
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 412
    assert ex.value.response["Error"]["Code"] == "DryRunOperation"
    assert (
        ex.value.response["Error"]["Message"]
        == "An error occurred (DryRunOperation) when calling the AuthorizeSecurityGroupEgress operation: Request would have succeeded, but DryRun flag is set"
    )

    egress_security_group.authorize_egress(IpPermissions=egress_permissions)

    assert egress_security_group.ip_permissions_egress[0]["FromPort"] == 22
    assert egress_security_group.ip_permissions_egress[0]["IpProtocol"] == "tcp"
    assert egress_security_group.ip_permissions_egress[0]["ToPort"] == 2222
    assert egress_security_group.ip_permissions_egress[0]["IpRanges"] == [
        {"CidrIp": "123.123.123.123/32"}
    ]

    # Bad group must produce error
    with pytest.raises(ClientError) as ex:
        client.revoke_security_group_egress(GroupId="badcompany")
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "InvalidGroup.NotFound"

    # Wrong Cidr should throw error
    with pytest.raises(ClientError) as ex:
        wrong_permissions = copy.deepcopy(egress_permissions)
        wrong_permissions[0]["IpRanges"][0]["CidrIp"] = "123.123.123.122/32"
        security_group.revoke_egress(IpPermissions=wrong_permissions)
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "InvalidPermission.NotFound"

    # Actually revoke
    with pytest.raises(ClientError) as ex:
        egress_security_group.revoke_egress(
            IpPermissions=egress_permissions, DryRun=True
        )
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 412
    assert ex.value.response["Error"]["Code"] == "DryRunOperation"
    assert (
        ex.value.response["Error"]["Message"]
        == "An error occurred (DryRunOperation) when calling the RevokeSecurityGroupEgress operation: Request would have succeeded, but DryRun flag is set"
    )

    egress_security_group.revoke_egress(IpPermissions=egress_permissions)

    egress_security_group = client.describe_security_groups()["SecurityGroups"][0]
    # There is still the default outbound rule
    assert len(egress_security_group["IpPermissionsEgress"]) == 1


@mock_aws
def test_authorize_other_group_and_revoke():
    ec2 = boto3.resource("ec2", REGION)
    client = boto3.client("ec2", REGION)
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
    assert found_sec_group["IpPermissions"][0]["ToPort"] == 2222
    assert (
        found_sec_group["IpPermissions"][0]["UserIdGroupPairs"][0]["GroupId"]
        == other_security_group.id
    )

    # Wrong source group should throw error
    with pytest.raises(ClientError) as ex:
        wrong_permissions = copy.deepcopy(permissions)
        wrong_permissions[0]["UserIdGroupPairs"][0]["GroupId"] = "unknown"
        security_group.revoke_ingress(IpPermissions=wrong_permissions)
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "InvalidGroup.NotFound"

    # Bad group must produce error
    with pytest.raises(ClientError) as ex:
        client.revoke_security_group_ingress(GroupId="badcompany")
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "InvalidGroup.NotFound"

    # Actually revoke
    security_group.revoke_ingress(IpPermissions=permissions)

    found_sec_group = client.describe_security_groups(GroupNames=[sg_name])[
        "SecurityGroups"
    ][0]
    assert len(found_sec_group["IpPermissions"]) == 0


@mock_aws
def test_authorize_other_group_egress_and_revoke():
    ec2 = boto3.resource("ec2", region_name=REGION)

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
    assert len(sg01.ip_permissions_egress) == 2
    assert ip_permission in sg01.ip_permissions_egress

    sg01.revoke_egress(IpPermissions=[org_ip_permission])
    assert len(sg01.ip_permissions_egress) == 1


@mock_aws
def test_authorize_group_in_vpc():
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
    assert found_sec_group["IpPermissions"][0]["ToPort"] == 2222
    assert (
        found_sec_group["IpPermissions"][0]["UserIdGroupPairs"][0]["GroupId"]
        == other_security_group.id
    )

    # Now remove the rule
    security_group.revoke_ingress(IpPermissions=permissions)

    # And check that it gets revoked
    found_sec_group = client.describe_security_groups(GroupNames=[sec_name1])[
        "SecurityGroups"
    ][0]
    assert len(found_sec_group["IpPermissions"]) == 0


@mock_aws
def test_describe_security_groups():
    ec2 = boto3.resource("ec2", REGION)
    client = boto3.client("ec2", REGION)
    vpc_id = f"vpc-{str(uuid4())[0:6]}"
    name_1 = str(uuid4())
    desc_1 = str(uuid4())
    sg1 = ec2.create_security_group(GroupName=name_1, Description=desc_1, VpcId=vpc_id)
    sg2 = ec2.create_security_group(GroupName=str(uuid4()), Description="test desc 2")

    resp = client.describe_security_groups(GroupNames=[name_1])["SecurityGroups"]
    assert len(resp) == 1
    assert resp[0]["GroupId"] == sg1.id

    with pytest.raises(ClientError) as ex:
        client.describe_security_groups(GroupNames=["does_not_exist"])
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "InvalidGroup.NotFound"

    resp = client.describe_security_groups(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
    )["SecurityGroups"]
    assert len(resp) == 1
    assert resp[0]["GroupId"] == sg1.id

    resp = client.describe_security_groups(
        Filters=[{"Name": "description", "Values": [desc_1]}]
    )["SecurityGroups"]
    assert len(resp) == 1
    assert resp[0]["GroupId"] == sg1.id

    all_sgs = retrieve_all_sgs(client)
    sg_ids = [sg["GroupId"] for sg in all_sgs]
    assert sg1.id in sg_ids
    assert sg2.id in sg_ids


@mock_aws
def test_authorize_bad_cidr_throws_invalid_parameter_value():
    ec2 = boto3.resource("ec2", REGION)
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
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "InvalidParameterValue"


@mock_aws
def test_security_group_tag_filtering():
    ec2 = boto3.resource("ec2", region_name=REGION)
    client = boto3.client("ec2", region_name=REGION)
    sg = ec2.create_security_group(GroupName=str(uuid4()), Description="Test SG")
    tag_name = str(uuid4())[0:6]
    tag_val = str(uuid4())
    sg.create_tags(Tags=[{"Key": tag_name, "Value": tag_val}])

    groups = client.describe_security_groups(
        Filters=[{"Name": f"tag:{tag_name}", "Values": [tag_val]}]
    )["SecurityGroups"]
    assert len(groups) == 1

    groups = client.describe_security_groups(
        Filters=[{"Name": f"tag:{tag_name}", "Values": ["unknown"]}]
    )["SecurityGroups"]
    assert len(groups) == 0


@mock_aws
def test_authorize_all_protocols_with_no_port_specification():
    ec2 = boto3.resource("ec2", region_name=REGION)
    client = boto3.client("ec2", region_name=REGION)
    sg_name = str(uuid4())
    sg = ec2.create_security_group(GroupName=sg_name, Description="test desc")

    permissions = [{"IpProtocol": "-1", "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}]
    sg.authorize_ingress(IpPermissions=permissions)

    sg = client.describe_security_groups(GroupNames=[sg_name])["SecurityGroups"][0]
    permission = sg["IpPermissions"][0]
    assert permission["IpProtocol"] == "-1"
    assert permission["IpRanges"] == [{"CidrIp": "0.0.0.0/0"}]
    assert "FromPort" not in permission
    assert "ToPort" not in permission


@mock_aws
def test_security_group_rule_filtering_group_id():
    ec2 = boto3.resource("ec2", REGION)
    client = boto3.client("ec2", REGION)
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")

    sg_name = str(uuid4())
    sg = client.create_security_group(
        Description="Test SG", GroupName=sg_name, VpcId=vpc.id
    )

    response = client.describe_security_group_rules(
        Filters=[{"Name": "group-id", "Values": [sg["GroupId"]]}]
    )
    rule_id = response["SecurityGroupRules"][0]["SecurityGroupRuleId"]

    tag_name = str(uuid4())[0:6]
    tag_val = str(uuid4())

    client.create_tags(Resources=[rule_id], Tags=[{"Key": tag_name, "Value": tag_val}])

    response = client.describe_security_group_rules(
        Filters=[{"Name": "group-id", "Values": [sg["GroupId"]]}]
    )
    assert "Tags" in response["SecurityGroupRules"][0]
    assert response["SecurityGroupRules"][0]["Tags"][0]["Key"] == tag_name
    assert response["SecurityGroupRules"][0]["Tags"][0]["Value"] == tag_val


@mock_aws
def test_security_group_rule_filtering_tags():
    # Setup
    ec2 = boto3.resource("ec2", REGION)
    client = boto3.client("ec2", REGION)
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    tags = [
        {"Key": "Automation", "Value": "Lambda"},
        {"Key": "Partner", "Value": "test"},
    ]

    sg_name = str(uuid4())
    sg = client.create_security_group(
        Description="Test SG",
        GroupName=sg_name,
        VpcId=vpc.id,
    )

    # Execute
    response1 = client.authorize_security_group_ingress(
        GroupId=sg["GroupId"],
        IpPermissions=[
            {
                "IpProtocol": "tcp",
                "FromPort": 80,
                "ToPort": 80,
                "IpRanges": [
                    {"CidrIp": "1.2.3.4/32", "Description": "Test description"}
                ],
            }
        ],
        TagSpecifications=[{"ResourceType": "security-group-rule", "Tags": tags}],
    )

    response2 = client.describe_security_group_rules(
        Filters=[{"Name": "tag:Partner", "Values": ["test"]}]
    )

    # Verify
    assert response1["SecurityGroupRules"][0]["Tags"] == tags
    assert "Tags" in response2["SecurityGroupRules"][0]
    assert response2["SecurityGroupRules"][0]["Tags"][1]["Key"] == "Partner"
    assert response2["SecurityGroupRules"][0]["Tags"][1]["Value"] == "test"


@mock_aws
def test_create_and_describe_security_grp_rule():
    ec2 = boto3.resource("ec2", REGION)
    client = boto3.client("ec2", REGION)
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")

    sg_name = str(uuid4())
    sg = client.create_security_group(
        Description="Test SG", GroupName=sg_name, VpcId=vpc.id
    )

    response = client.describe_security_group_rules(
        Filters=[{"Name": "group-id", "Values": [sg["GroupId"]]}]
    )
    rules = response["SecurityGroupRules"]

    # Only the default rule is present
    assert len(rules) == 1

    # Test default egress rule content
    assert rules[0]["IsEgress"] is True
    assert rules[0]["IpProtocol"] == "-1"
    assert rules[0]["CidrIpv4"] == "0.0.0.0/0"
    assert "GroupId" in rules[0]


@mock_aws
@pytest.mark.parametrize("use_vpc", [True, False], ids=["Use VPC", "Without VPC"])
def test_sec_group_rule_limit(use_vpc):
    ec2 = boto3.resource("ec2", region_name=REGION)
    client = boto3.client("ec2", region_name=REGION)

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
                "IpRanges": [{"CidrIp": f"{i}.0.0.0/0"} for i in range(110)],
            }
        ]
        client.authorize_security_group_ingress(
            GroupId=sg.id, IpPermissions=ip_permissions
        )
    assert ex.value.response["Error"]["Code"] == "RulesPerSecurityGroupLimitExceeded"

    sg.reload()
    assert sg.ip_permissions == []
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
            "IpRanges": [{"CidrIp": f"{i}.0.0.0/0"} for i in range(limit - 1)],
        }
    ]
    client.authorize_security_group_ingress(GroupId=sg.id, IpPermissions=permissions)
    # verify that we cannot authorize past the limit for a CIDR IP
    with pytest.raises(ClientError) as ex:
        permissions = [{"IpProtocol": "-1", "IpRanges": [{"CidrIp": "100.0.0.0/0"}]}]
        client.authorize_security_group_ingress(
            GroupId=sg.id, IpPermissions=permissions
        )
    assert ex.value.response["Error"]["Code"] == "RulesPerSecurityGroupLimitExceeded"
    # verify that we cannot authorize past the limit for a different sec group
    with pytest.raises(ClientError) as ex:
        client.authorize_security_group_ingress(
            GroupId=sg.id, IpPermissions=other_permissions
        )
    assert ex.value.response["Error"]["Code"] == "RulesPerSecurityGroupLimitExceeded"

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
            "IpRanges": [{"CidrIp": f"{i}.0.0.0/0"} for i in range(1, limit - 1)],
        }
    ]
    client.authorize_security_group_egress(GroupId=sg.id, IpPermissions=permissions)
    # verify that we cannot authorize past the limit for a CIDR IP
    with pytest.raises(ClientError) as ex:
        permissions = [{"IpProtocol": "-1", "IpRanges": [{"CidrIp": "101.0.0.0/0"}]}]
        client.authorize_security_group_egress(GroupId=sg.id, IpPermissions=permissions)
    assert ex.value.response["Error"]["Code"] == "RulesPerSecurityGroupLimitExceeded"
    # verify that we cannot authorize past the limit for a different sec group
    with pytest.raises(ClientError) as ex:
        client.authorize_security_group_egress(
            GroupId=sg.id, IpPermissions=other_permissions
        )
    assert ex.value.response["Error"]["Code"] == "RulesPerSecurityGroupLimitExceeded"


@mock_aws
def test_add_same_rule_twice_throws_error():
    ec2 = boto3.resource("ec2", region_name=REGION)

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
    assert ex.value.response["Error"]["Code"] == "InvalidPermission.Duplicate"

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
    assert ex.value.response["Error"]["Code"] == "InvalidPermission.Duplicate"


@mock_aws
def test_description_in_ip_permissions():
    ec2 = boto3.resource("ec2", region_name=REGION)
    conn = boto3.client("ec2", region_name=REGION)
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    sg = conn.create_security_group(
        GroupName="sg1", Description="Test security group sg1", VpcId=vpc.id
    )

    ip_permissions = [
        {
            "IpProtocol": "tcp",
            "FromPort": 27017,
            "ToPort": 27018,
            "IpRanges": [
                {"CidrIp": "1.2.3.4/32", "Description": "austin"},
                {"CidrIp": "2.3.4.5/32", "Description": "powers"},
            ],
        }
    ]
    conn.authorize_security_group_ingress(
        GroupId=sg["GroupId"], IpPermissions=ip_permissions
    )

    result = conn.describe_security_group_rules(
        Filters=[{"Name": "group-id", "Values": [sg["GroupId"]]}]
    )
    assert len(result["SecurityGroupRules"]) == 3

    assert result["SecurityGroupRules"][0]["Description"] == "austin"
    assert result["SecurityGroupRules"][0]["CidrIpv4"] == "1.2.3.4/32"
    assert result["SecurityGroupRules"][0]["IsEgress"] is False
    assert result["SecurityGroupRules"][0]["FromPort"] == 27017
    assert result["SecurityGroupRules"][0]["ToPort"] == 27018

    assert result["SecurityGroupRules"][1]["Description"] == "powers"
    assert result["SecurityGroupRules"][1]["CidrIpv4"] == "2.3.4.5/32"
    assert result["SecurityGroupRules"][1]["IsEgress"] is False
    assert result["SecurityGroupRules"][1]["FromPort"] == 27017
    assert result["SecurityGroupRules"][1]["ToPort"] == 27018

    assert result["SecurityGroupRules"][2]["Description"] == ""
    assert result["SecurityGroupRules"][2]["IsEgress"] is True
    assert result["SecurityGroupRules"][2]["FromPort"] == -1
    assert result["SecurityGroupRules"][2]["ToPort"] == -1

    result = conn.describe_security_groups(GroupIds=[sg["GroupId"]])
    group = result["SecurityGroups"][0]

    assert group["IpPermissions"][0]["IpRanges"][0]["Description"] == "austin"
    assert group["IpPermissions"][0]["IpRanges"][0]["CidrIp"] == "1.2.3.4/32"

    assert group["IpPermissions"][0]["IpRanges"][1]["Description"] == "powers"
    assert group["IpPermissions"][0]["IpRanges"][1]["CidrIp"] == "2.3.4.5/32"

    sg = conn.create_security_group(
        GroupName="sg2", Description="Test security group sg1", VpcId=vpc.id
    )

    ip_permissions = [
        {
            "IpProtocol": "tcp",
            "FromPort": 27019,
            "ToPort": 27019,
            "IpRanges": [{"CidrIp": "3.4.5.6/32"}],
        }
    ]
    conn.authorize_security_group_ingress(
        GroupId=sg["GroupId"], IpPermissions=ip_permissions
    )

    result = conn.describe_security_groups(GroupIds=[sg["GroupId"]])
    group = result["SecurityGroups"][0]

    assert group["IpPermissions"][0]["IpRanges"][0].get("Description") is None
    assert group["IpPermissions"][0]["IpRanges"][0]["CidrIp"] == "3.4.5.6/32"


@mock_aws
def test_security_group_tagging():
    conn = boto3.client("ec2", region_name=REGION)

    sg = conn.create_security_group(GroupName=str(uuid4()), Description="Test SG")

    with pytest.raises(ClientError) as ex:
        conn.create_tags(
            Resources=[sg["GroupId"]],
            Tags=[{"Key": "Test", "Value": "Tag"}],
            DryRun=True,
        )
    assert ex.value.response["Error"]["Code"] == "DryRunOperation"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 412
    assert (
        ex.value.response["Error"]["Message"]
        == "An error occurred (DryRunOperation) when calling the CreateTags operation: Request would have succeeded, but DryRun flag is set"
    )

    tag_val = str(uuid4())
    conn.create_tags(
        Resources=[sg["GroupId"]], Tags=[{"Key": "Test", "Value": tag_val}]
    )
    describe = conn.describe_security_groups(
        Filters=[{"Name": "tag-value", "Values": [tag_val]}]
    )
    tag = describe["SecurityGroups"][0]["Tags"][0]
    assert tag["Value"] == tag_val
    assert tag["Key"] == "Test"


@mock_aws
def test_security_group_wildcard_tag_filter():
    conn = boto3.client("ec2", region_name=REGION)
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
    assert tag["Value"] == tag_val
    assert tag["Key"] == "Test"


@mock_aws
def test_security_group_filter_ip_permission():
    ec2 = boto3.resource("ec2", region_name=REGION)
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")

    conn = boto3.client("ec2", region_name=REGION)
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
    assert len(describe) == 1

    assert describe[0]["GroupName"] == sg_name


def retrieve_all_sgs(conn, filters=[]):  # pylint: disable=W0102
    res = conn.describe_security_groups(Filters=filters)
    all_groups = res["SecurityGroups"]
    next_token = res.get("NextToken")
    while next_token:
        res = conn.describe_security_groups(Filters=filters)
        all_groups.extend(res["SecurityGroups"])
        next_token = res.get("NextToken")
    return all_groups


@mock_aws
def test_authorize_and_revoke_in_bulk():
    ec2 = boto3.resource("ec2", region_name=REGION)

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
    assert len(sg01.ip_permissions) == 4
    sorted_sg01_ip_permissions = json.dumps(sg01.ip_permissions, sort_keys=True)
    for ip_permission in expected_ip_permissions:
        assert ip_permission in sorted_sg01_ip_permissions

    sg01.revoke_ingress(IpPermissions=ip_permissions)
    assert sg01.ip_permissions == []
    for ip_permission in expected_ip_permissions:
        assert ip_permission not in sg01.ip_permissions

    sg01.authorize_egress(IpPermissions=org_ip_permissions)
    # Due to drift property of the Security Group,
    # rules with same Ip protocol, FromPort and ToPort will be merged together
    assert len(sg01.ip_permissions_egress) == 5
    sorted_sg01_ip_permissions_egress = json.dumps(
        sg01.ip_permissions_egress, sort_keys=True
    )
    for ip_permission in expected_ip_permissions:
        assert ip_permission in sorted_sg01_ip_permissions_egress

    sg01.revoke_egress(IpPermissions=ip_permissions)
    assert len(sg01.ip_permissions_egress) == 1
    for ip_permission in expected_ip_permissions:
        assert ip_permission not in sg01.ip_permissions_egress


@mock_aws
def test_security_group_ingress_without_multirule():
    ec2 = boto3.resource("ec2", "ca-central-1")
    client = boto3.client("ec2", "ca-central-1")
    sg = ec2.create_security_group(Description="Test SG", GroupName=str(uuid4()))

    assert len(sg.ip_permissions) == 0
    rule_id = sg.authorize_ingress(
        CidrIp="192.168.0.1/32", FromPort=22, ToPort=22, IpProtocol="tcp"
    )["SecurityGroupRules"][0]["SecurityGroupRuleId"]

    assert len(sg.ip_permissions) == 1

    rules = client.describe_security_group_rules(SecurityGroupRuleIds=[rule_id])[
        "SecurityGroupRules"
    ]
    ingress = [rule for rule in rules if rule["SecurityGroupRuleId"] == rule_id]
    assert len(ingress) == 1
    assert ingress[0]["IsEgress"] is False


@mock_aws
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


@mock_aws
def test_get_all_security_groups_filter_with_same_vpc_id():
    ec2 = boto3.resource("ec2", region_name=REGION)
    client = boto3.client("ec2", region_name=REGION)
    vpc_id = "vpc-5300000c"
    security_group = ec2.create_security_group(
        GroupName=str(uuid4()), Description="test1", VpcId=vpc_id
    )
    security_group2 = ec2.create_security_group(
        GroupName=str(uuid4()), Description="test2", VpcId=vpc_id
    )

    assert security_group.vpc_id == vpc_id
    assert security_group2.vpc_id == vpc_id

    security_groups = client.describe_security_groups(
        GroupIds=[security_group.id], Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
    )["SecurityGroups"]
    assert len(security_groups) == 1

    with pytest.raises(ClientError) as ex:
        client.describe_security_groups(GroupIds=["does_not_exist"])
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "InvalidGroup.NotFound"


@mock_aws
def test_revoke_security_group_egress():
    ec2 = boto3.resource("ec2", REGION)
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    sg = ec2.create_security_group(
        Description="Test SG", GroupName=str(uuid4()), VpcId=vpc.id
    )

    assert sg.ip_permissions_egress == [
        {
            "IpProtocol": "-1",
            "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
            "UserIdGroupPairs": [],
            "Ipv6Ranges": [],
            "PrefixListIds": [],
        }
    ]

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
    assert len(sg.ip_permissions_egress) == 0


@mock_aws
def test_revoke_security_group_egress__without_ipprotocol():
    ec2 = boto3.resource("ec2", "eu-west-2")
    client = boto3.client("ec2", region_name="eu-west-2")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    sec_group = client.describe_security_groups(
        Filters=[
            {"Name": "group-name", "Values": ["default"]},
            {"Name": "vpc-id", "Values": [vpc.id]},
        ]
    )["SecurityGroups"][0]["GroupId"]

    rule_id = client.describe_security_group_rules(
        Filters=[{"Name": "group-id", "Values": [sec_group]}]
    )["SecurityGroupRules"][0]["SecurityGroupRuleId"]

    client.revoke_security_group_egress(
        GroupId=sec_group, SecurityGroupRuleIds=[rule_id]
    )

    remaining_rules = client.describe_security_group_rules(
        Filters=[{"Name": "group-id", "Values": [sec_group]}]
    )["SecurityGroupRules"]
    assert len(remaining_rules) == 0


@mock_aws
def test_update_security_group_rule_descriptions_egress():
    ec2 = boto3.resource("ec2", REGION)
    client = boto3.client("ec2", REGION)
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    sg_name = str(uuid4())
    sg = ec2.create_security_group(
        Description="Test SG", GroupName=sg_name, VpcId=vpc.id
    )
    sg_id = sg.id

    ip_ranges = client.describe_security_groups(GroupIds=[sg_id])["SecurityGroups"][0][
        "IpPermissionsEgress"
    ][0]["IpRanges"]
    assert len(ip_ranges) == 1
    assert ip_ranges[0] == {"CidrIp": "0.0.0.0/0"}

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
    assert len(ip_ranges) == 1
    assert ip_ranges[0] == {"CidrIp": "0.0.0.0/0", "Description": "my d3scription"}


@mock_aws
def test_update_security_group_rule_descriptions_ingress():
    ec2 = boto3.resource("ec2", REGION)
    client = boto3.client("ec2", REGION)
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    sg_name = str(uuid4())
    sg = ec2.create_security_group(
        Description="Test SG", GroupName=sg_name, VpcId=vpc.id
    )
    sg_id = sg.id

    expected_ip_ranges = [
        {"CidrIp": "1.2.3.4/32", "Description": "first desc"},
        {"CidrIp": "1.2.3.5/32", "Description": "first desc"},
        {"CidrIp": "1.2.3.6/32", "Description": "first desc"},
    ]
    ip_permissions = [
        {
            "IpProtocol": "tcp",
            "FromPort": 27017,
            "ToPort": 27017,
            "IpRanges": expected_ip_ranges,
        }
    ]
    client.authorize_security_group_ingress(
        GroupId=sg_id,
        IpPermissions=ip_permissions,
    )
    client.describe_security_group_rules(
        Filters=[{"Name": "tag:Partner", "Values": ["test"]}]
    )
    ip_ranges = client.describe_security_groups(GroupIds=[sg_id])["SecurityGroups"][0][
        "IpPermissions"
    ][0]["IpRanges"]
    assert ip_ranges == expected_ip_ranges

    client.update_security_group_rule_descriptions_ingress(
        GroupName=sg_name,
        IpPermissions=[
            {
                "IpProtocol": "tcp",
                "FromPort": 27017,
                "ToPort": 27017,
                "IpRanges": [
                    {"CidrIp": "1.2.3.4/32", "Description": "second desc"},
                    {"CidrIp": "1.2.3.6/32", "Description": "third desc"},
                ],
            }
        ],
    )
    expected_ip_ranges[0]["Description"] = "second desc"
    expected_ip_ranges[2]["Description"] = "third desc"

    ip_ranges = client.describe_security_groups(GroupIds=[sg_id])["SecurityGroups"][0][
        "IpPermissions"
    ][0]["IpRanges"]
    assert ip_ranges == expected_ip_ranges


@mock_aws
def test_non_existent_security_group_raises_error_on_authorize():
    client = boto3.client("ec2", REGION)
    non_existent_sg = "sg-123abc"
    expected_error = f"The security group '{non_existent_sg}' does not exist"
    authorize_funcs = [
        client.authorize_security_group_egress,
        client.authorize_security_group_ingress,
    ]
    for authorize_func in authorize_funcs:
        with pytest.raises(ClientError) as ex:
            authorize_func(GroupId=non_existent_sg, IpPermissions=[{}])
        assert ex.value.response["Error"]["Code"] == "InvalidGroup.NotFound"
        assert ex.value.response["Error"]["Message"] == expected_error


@mock_aws
def test_security_group_rules_added_via_the_backend_can_be_revoked_via_the_api():
    if settings.TEST_SERVER_MODE:
        raise unittest.SkipTest("Can't test backend directly in server mode.")
    ec2_backend = ec2_backends[DEFAULT_ACCOUNT_ID][REGION]
    ec2_resource = boto3.resource("ec2", region_name=REGION)
    ec2_client = boto3.client("ec2", region_name=REGION)
    vpc = ec2_resource.create_vpc(CidrBlock="10.0.0.0/16")
    group_name = str(uuid4())
    sg = ec2_resource.create_security_group(
        GroupName=group_name, Description="test", VpcId=vpc.id
    )
    # Add an ingress/egress rule using the EC2 backend directly.
    rule_ingress = {
        "group_name_or_id": sg.id,
        "security_rule_ids": None,
        "from_port": 0,
        "ip_protocol": "udp",
        "ip_ranges": [],
        "to_port": 65535,
        "source_groups": [{"GroupId": sg.id}],
    }
    ec2_backend.authorize_security_group_ingress(**rule_ingress)
    rule_egress = {
        "group_name_or_id": sg.id,
        "security_rule_ids": None,
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


@mock_aws
def test_filter_description():
    ec2r = boto3.resource("ec2", region_name=REGION)
    vpc = ec2r.create_vpc(CidrBlock="10.250.0.0/16")

    unique = str(uuid4())
    sg1 = vpc.create_security_group(
        Description=(f"A {unique} Description"), GroupName="test-1"
    )
    vpc.create_security_group(
        Description="Another Description That Awes The Human Mind", GroupName="test-2"
    )

    filter_to_match_group_1_description = {
        "Name": "description",
        "Values": [f"*{unique}*"],
    }

    security_groups = ec2r.security_groups.filter(
        Filters=[filter_to_match_group_1_description]
    )

    security_groups = list(security_groups)
    assert len(security_groups) == 1
    assert security_groups[0].group_id == sg1.group_id


@mock_aws
def test_filter_ip_permission__cidr():
    if settings.TEST_SERVER_MODE:
        raise SkipTest(
            "CIDR's might already exist due to other tests creating IP ranges"
        )
    ec2r = boto3.resource("ec2", region_name=REGION)
    vpc = ec2r.create_vpc(CidrBlock="10.250.1.0/16")

    sg1 = vpc.create_security_group(
        Description="A Described Description Descriptor", GroupName="test-1"
    )
    sg2 = vpc.create_security_group(
        Description="Another Description That Awes The Human Mind", GroupName="test-2"
    )

    sg1.authorize_ingress(
        IpPermissions=[
            {
                "FromPort": 7357,
                "ToPort": 7357,
                "IpProtocol": "tcp",
                "IpRanges": [{"CidrIp": "10.250.0.0/16"}, {"CidrIp": "10.251.0.0/16"}],
            }
        ]
    )
    sg2.authorize_ingress(
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
        "Name": "ip-permission.cidr",
        "Values": ["10.250.0.0/16"],
    }
    security_groups = ec2r.security_groups.filter(Filters=[filter_to_match_group_1])

    security_groups = list(security_groups)
    assert len(security_groups) == 1
    assert security_groups[0].group_id == sg1.group_id


@mock_aws
def test_filter_egress__ip_permission__cidr():
    if settings.TEST_SERVER_MODE:
        raise SkipTest(
            "CIDR's might already exist due to other tests creating IP ranges"
        )
    ec2r = boto3.resource("ec2", region_name=REGION)
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


@mock_aws
def test_filter_egress__ip_permission__from_port():
    ec2r = boto3.resource("ec2", region_name=REGION)
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
    assert sg1.group_id in [s.group_id for s in security_groups]
    assert sg2.group_id not in [s.group_id for s in security_groups]


@mock_aws
def test_filter_egress__ip_permission__group_id():
    ec2r = boto3.resource("ec2", region_name=REGION)
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


@mock_aws
def test_filter_egress__ip_permission__group_name_create_with_id_filter_by_name():
    """
    this fails to find the group in the AWS API, so we should also fail to find it
    """
    ec2r = boto3.resource("ec2", region_name=REGION)
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


@mock_aws
def test_filter_egress__ip_permission__group_name_create_with_id_filter_by_id():
    ec2r = boto3.resource("ec2", region_name=REGION)
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


@mock_aws
def test_filter_egress__ip_permission__protocol():
    ec2r = boto3.resource("ec2", region_name=REGION)
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
    assert sg1.group_id in group_ids
    assert sg2.group_id not in group_ids


@mock_aws
def test_filter_egress__ip_permission__to_port():
    ec2r = boto3.resource("ec2", region_name=REGION)
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
    assert sg1.group_id in [s.group_id for s in security_groups]
    assert sg2.group_id not in [s.group_id for s in security_groups]


@mock_aws
def test_get_groups_by_ippermissions_group_id_filter():
    ec2r = boto3.resource("ec2", region_name=REGION)
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


@mock_aws
def test_get_groups_by_ippermissions_group_id_filter_across_vpcs():
    # setup 2 VPCs, each with a single Security Group
    # where one security group authorizes the other sg (in another vpc) via GroupId
    ec2r = boto3.resource("ec2", region_name=REGION)

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


@mock_aws
def test_filter_group_name():
    """
    this filter is an exact match, not a glob
    """
    ec2r = boto3.resource("ec2", region_name=REGION)
    vpc = ec2r.create_vpc(CidrBlock="10.250.1.0/16")

    uniq_sg_name_prefix = str(uuid4())[0:6]
    sg1 = vpc.create_security_group(
        Description="A Described Description Descriptor",
        GroupName=f"{uniq_sg_name_prefix}-test-1",
    )
    vpc.create_security_group(
        Description="Another Description That Awes The Human Mind",
        GroupName=f"{uniq_sg_name_prefix}-test-12",
    )
    vpc.create_security_group(
        Description="Yet Another Descriptive Description",
        GroupName=f"{uniq_sg_name_prefix}-test-13",
    )
    vpc.create_security_group(
        Description="Such Description Much Described",
        GroupName=f"{uniq_sg_name_prefix}-test-14",
    )

    filter_to_match_group_1 = {
        "Name": "group-name",
        "Values": [sg1.group_name],
    }
    security_groups = ec2r.security_groups.filter(Filters=[filter_to_match_group_1])

    security_groups = list(security_groups)
    assert len(security_groups) == 1
    assert security_groups[0].group_name == sg1.group_name


@mock_aws
def test_revoke_security_group_ingress():
    ec2 = boto3.client("ec2", region_name=REGION)

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")

    sg = ec2.create_security_group(
        Description="Test SG", GroupName=str(uuid4()), VpcId=vpc["Vpc"]["VpcId"]
    )
    sg_id = sg["GroupId"]

    ec2.authorize_security_group_ingress(
        GroupId=sg_id,
        IpPermissions=[
            {
                "FromPort": 3000,
                "ToPort": 3300,
                "IpProtocol": "TCP",
                "IpRanges": [{"CidrIp": "10.0.0.1/32"}],
            },
            {
                "FromPort": 8080,
                "ToPort": 8080,
                "IpProtocol": "TCP",
                "IpRanges": [{"CidrIp": "10.0.0.1/32"}],
            },
        ],
    )

    response = ec2.describe_security_group_rules(
        Filters=[{"Name": "group-id", "Values": [sg_id]}]
    )

    ingress_rules = [r for r in response["SecurityGroupRules"] if not r["IsEgress"]]
    assert len(ingress_rules) == 2

    # revoke 1 of the 2 ingress rules
    ec2.revoke_security_group_ingress(
        GroupId=sg_id, SecurityGroupRuleIds=[ingress_rules[0]["SecurityGroupRuleId"]]
    )

    response = ec2.describe_security_group_rules(
        Filters=[{"Name": "group-id", "Values": [sg_id]}]
    )

    ingress_rules = [r for r in response["SecurityGroupRules"] if not r["IsEgress"]]
    assert len(ingress_rules) == 1


@mock_aws()
def test_invalid_security_group_id_in_rules_search():
    ec2 = boto3.client("ec2", region_name=REGION)

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    vpc_id = vpc["Vpc"]["VpcId"]
    group_name = "test-group"

    response = ec2.create_security_group(
        Description="Inventing a security group", GroupName=group_name, VpcId=vpc_id
    )
    group_id = response["GroupId"]

    # assert error with invalid sg id
    with pytest.raises(ClientError) as e:
        ec2.describe_security_group_rules(
            Filters=[{"Name": "group-id", "Values": ["foobar"]}]
        )
    error = e.value.response["Error"]
    assert "InvalidGroupId.Malformed" == error["Code"]
    assert "The security group ID 'foobar' is malformed" in error["Message"]

    # assert with non-existent sg
    response = ec2.describe_security_group_rules(
        Filters=[{"Name": "group-id", "Values": ["sg-005216b55886f0fdc"]}]
    )
    assert len(response["SecurityGroupRules"]) == 0

    # assert with no rules
    response = ec2.describe_security_group_rules(
        Filters=[{"Name": "group-id", "Values": [group_id]}]
    )
    assert len(response["SecurityGroupRules"]) == 1
