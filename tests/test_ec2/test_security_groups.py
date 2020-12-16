from __future__ import unicode_literals

import copy
import json

# Ensure 'pytest.raises' context manager support for Python 2.6
import pytest

import boto3
import boto
from botocore.exceptions import ClientError
from boto.exception import EC2ResponseError
import sure  # noqa

from moto import mock_ec2, mock_ec2_deprecated


@mock_ec2_deprecated
def test_create_and_describe_security_group():
    conn = boto.connect_ec2("the_key", "the_secret")

    with pytest.raises(EC2ResponseError) as ex:
        security_group = conn.create_security_group(
            "test security group", "this is a test security group", dry_run=True
        )
    ex.value.error_code.should.equal("DryRunOperation")
    ex.value.status.should.equal(400)
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
    all_groups.should.have.length_of(3)
    group_names = [group.name for group in all_groups]
    set(group_names).should.equal(set(["default", "test security group"]))


@mock_ec2_deprecated
def test_create_security_group_without_description_raises_error():
    conn = boto.connect_ec2("the_key", "the_secret")

    with pytest.raises(EC2ResponseError) as cm:
        conn.create_security_group("test security group", "")
    cm.value.code.should.equal("MissingParameter")
    cm.value.status.should.equal(400)
    cm.value.request_id.should_not.be.none


@mock_ec2_deprecated
def test_default_security_group():
    conn = boto.ec2.connect_to_region("us-east-1")
    groups = conn.get_all_security_groups()
    groups.should.have.length_of(2)
    groups[0].name.should.equal("default")


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

    all_groups = conn.get_all_security_groups(filters={"vpc_id": [vpc_id]})

    all_groups[0].vpc_id.should.equal(vpc_id)

    all_groups.should.have.length_of(1)
    all_groups[0].name.should.equal("test security group")


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

    all_groups.should.have.length_of(4)
    group_names = [group.name for group in all_groups]
    # The default group is created automatically
    set(group_names).should.equal(set(["default", "test security group"]))


@mock_ec2
def test_create_two_security_groups_in_vpc_with_ipv6_enabled():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16", AmazonProvidedIpv6CidrBlock=True)

    security_group = ec2.create_security_group(
        GroupName="sg01", Description="Test security group sg01", VpcId=vpc.id
    )

    # The security group must have two defaul egress rules (one for ipv4 and aonther for ipv6)
    security_group.ip_permissions_egress.should.have.length_of(2)


@mock_ec2_deprecated
def test_deleting_security_groups():
    conn = boto.connect_ec2("the_key", "the_secret")
    security_group1 = conn.create_security_group("test1", "test1")
    conn.create_security_group("test2", "test2")

    conn.get_all_security_groups().should.have.length_of(4)

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
    ex.value.status.should.equal(400)
    ex.value.message.should.equal(
        "An error occurred (DryRunOperation) when calling the DeleteSecurityGroup operation: Request would have succeeded, but DryRun flag is set"
    )

    conn.delete_security_group("test2")
    conn.get_all_security_groups().should.have.length_of(3)

    # Delete by group id
    conn.delete_security_group(group_id=security_group1.id)
    conn.get_all_security_groups().should.have.length_of(2)


@mock_ec2_deprecated
def test_delete_security_group_in_vpc():
    conn = boto.connect_ec2("the_key", "the_secret")
    vpc_id = "vpc-12345"
    security_group1 = conn.create_security_group("test1", "test1", vpc_id)

    # this should not throw an exception
    conn.delete_security_group(group_id=security_group1.id)


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
    ex.value.status.should.equal(400)
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
    ex.value.status.should.equal(400)
    ex.value.message.should.equal(
        "An error occurred (DryRunOperation) when calling the RevokeSecurityGroupIngress operation: Request would have succeeded, but DryRun flag is set"
    )

    security_group.revoke(
        ip_protocol="tcp", from_port="22", to_port="2222", cidr_ip="123.123.123.123/32"
    )

    security_group = conn.get_all_security_groups()[0]
    security_group.rules.should.have.length_of(0)

    # Test for egress as well
    egress_security_group = conn.create_security_group(
        "testegress", "testegress", vpc_id="vpc-3432589"
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
    ex.value.status.should.equal(400)
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
    # Deal with Python2 dict->unicode, instead of dict->string
    if type(actual_cidr) == "unicode":
        actual_cidr = json.loads(actual_cidr.replace("u'", "'").replace("'", '"'))
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
    ex.value.status.should.equal(400)
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

    egress_security_group = conn.get_all_security_groups()[0]
    # There is still the default outbound rule
    egress_security_group.rules_egress.should.have.length_of(1)


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
def test_authorize_other_group_egress_and_revoke():
    ec2 = boto3.resource("ec2", region_name="us-west-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")

    sg01 = ec2.create_security_group(
        GroupName="sg01", Description="Test security group sg01", VpcId=vpc.id
    )
    sg02 = ec2.create_security_group(
        GroupName="sg02", Description="Test security group sg02", VpcId=vpc.id
    )

    ip_permission = {
        "IpProtocol": "tcp",
        "FromPort": 27017,
        "ToPort": 27017,
        "UserIdGroupPairs": [
            {"GroupId": sg02.id, "GroupName": "sg02", "UserId": sg02.owner_id}
        ],
        "IpRanges": [],
    }

    sg01.authorize_egress(IpPermissions=[ip_permission])
    sg01.ip_permissions_egress.should.have.length_of(2)
    sg01.ip_permissions_egress.should.contain(ip_permission)

    sg01.revoke_egress(IpPermissions=[ip_permission])
    sg01.ip_permissions_egress.should.have.length_of(1)


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

    resp = conn.get_all_security_groups(filters={"vpc_id": ["vpc-mjm05d27"]})
    resp.should.have.length_of(1)
    resp[0].id.should.equal(sg1.id)

    resp = conn.get_all_security_groups(filters={"description": ["test1"]})
    resp.should.have.length_of(1)
    resp[0].id.should.equal(sg1.id)

    resp = conn.get_all_security_groups()
    resp.should.have.length_of(4)


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


@mock_ec2_deprecated
def test_security_group_tagging():
    conn = boto.connect_vpc()
    vpc = conn.create_vpc("10.0.0.0/16")

    sg = conn.create_security_group("test-sg", "Test SG", vpc.id)

    with pytest.raises(EC2ResponseError) as ex:
        sg.add_tag("Test", "Tag", dry_run=True)
    ex.value.error_code.should.equal("DryRunOperation")
    ex.value.status.should.equal(400)
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


@mock_ec2_deprecated
def test_security_group_tag_filtering():
    conn = boto.connect_ec2()
    sg = conn.create_security_group("test-sg", "Test SG")
    sg.add_tag("test-tag", "test-value")

    groups = conn.get_all_security_groups(filters={"tag:test-tag": "test-value"})
    groups.should.have.length_of(1)


@mock_ec2_deprecated
def test_authorize_all_protocols_with_no_port_specification():
    conn = boto.connect_ec2()
    sg = conn.create_security_group("test", "test")

    success = sg.authorize(ip_protocol="-1", cidr_ip="0.0.0.0/0")
    success.should.be.true

    sg = conn.get_all_security_groups("test")[0]
    sg.rules[0].from_port.should.equal(None)
    sg.rules[0].to_port.should.equal(None)


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
        cidr_ip=["{0}.0.0.0/0".format(i) for i in range(99)],
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
    # fill the rules up the limit
    # remember that by default, when created a sec group contains 1 egress rule
    # so our other_sg rule + 98 CIDR IP rules + 1 by default == 100 the limit
    for i in range(98):
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
        cidr_ip=["{0}.0.0.0/0".format(i) for i in range(49)],
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
    for i in range(48):
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

    sg = conn.create_security_group(GroupName="test-sg", Description="Test SG")

    with pytest.raises(ClientError) as ex:
        conn.create_tags(
            Resources=[sg["GroupId"]],
            Tags=[{"Key": "Test", "Value": "Tag"}],
            DryRun=True,
        )
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the CreateTags operation: Request would have succeeded, but DryRun flag is set"
    )

    conn.create_tags(Resources=[sg["GroupId"]], Tags=[{"Key": "Test", "Value": "Tag"}])
    describe = conn.describe_security_groups(
        Filters=[{"Name": "tag-value", "Values": ["Tag"]}]
    )
    tag = describe["SecurityGroups"][0]["Tags"][0]
    tag["Value"].should.equal("Tag")
    tag["Key"].should.equal("Test")


@mock_ec2
def test_security_group_wildcard_tag_filter_boto3():
    conn = boto3.client("ec2", region_name="us-east-1")
    sg = conn.create_security_group(GroupName="test-sg", Description="Test SG")
    conn.create_tags(Resources=[sg["GroupId"]], Tags=[{"Key": "Test", "Value": "Tag"}])
    describe = conn.describe_security_groups(
        Filters=[{"Name": "tag-value", "Values": ["*"]}]
    )

    tag = describe["SecurityGroups"][0]["Tags"][0]
    tag["Value"].should.equal("Tag")
    tag["Key"].should.equal("Test")


@mock_ec2
def test_authorize_and_revoke_in_bulk():
    ec2 = boto3.resource("ec2", region_name="us-west-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")

    sg01 = ec2.create_security_group(
        GroupName="sg01", Description="Test security group sg01", VpcId=vpc.id
    )
    sg02 = ec2.create_security_group(
        GroupName="sg02", Description="Test security group sg02", VpcId=vpc.id
    )
    sg03 = ec2.create_security_group(
        GroupName="sg03", Description="Test security group sg03"
    )
    sg04 = ec2.create_security_group(
        GroupName="sg04", Description="Test security group sg04"
    )
    ip_permissions = [
        {
            "IpProtocol": "tcp",
            "FromPort": 27017,
            "ToPort": 27017,
            "UserIdGroupPairs": [
                {"GroupId": sg02.id, "GroupName": "sg02", "UserId": sg02.owner_id}
            ],
            "IpRanges": [],
        },
        {
            "IpProtocol": "tcp",
            "FromPort": 27018,
            "ToPort": 27018,
            "UserIdGroupPairs": [{"GroupId": sg02.id, "UserId": sg02.owner_id}],
            "IpRanges": [],
        },
        {
            "IpProtocol": "tcp",
            "FromPort": 27017,
            "ToPort": 27017,
            "UserIdGroupPairs": [{"GroupName": "sg03", "UserId": sg03.owner_id}],
            "IpRanges": [],
        },
        {
            "IpProtocol": "tcp",
            "FromPort": 27015,
            "ToPort": 27015,
            "UserIdGroupPairs": [{"GroupName": "sg04", "UserId": sg04.owner_id}],
            "IpRanges": [
                {"CidrIp": "10.10.10.0/24", "Description": "Some Description"}
            ],
        },
        {
            "IpProtocol": "tcp",
            "FromPort": 27016,
            "ToPort": 27016,
            "UserIdGroupPairs": [{"GroupId": sg04.id, "UserId": sg04.owner_id}],
            "IpRanges": [{"CidrIp": "10.10.10.0/24"}],
        },
    ]
    expected_ip_permissions = copy.deepcopy(ip_permissions)
    expected_ip_permissions[1]["UserIdGroupPairs"][0]["GroupName"] = "sg02"
    expected_ip_permissions[2]["UserIdGroupPairs"][0]["GroupId"] = sg03.id
    expected_ip_permissions[3]["UserIdGroupPairs"][0]["GroupId"] = sg04.id
    expected_ip_permissions[4]["UserIdGroupPairs"][0]["GroupName"] = "sg04"

    sg01.authorize_ingress(IpPermissions=ip_permissions)
    sg01.ip_permissions.should.have.length_of(5)
    for ip_permission in expected_ip_permissions:
        sg01.ip_permissions.should.contain(ip_permission)

    sg01.revoke_ingress(IpPermissions=ip_permissions)
    sg01.ip_permissions.should.be.empty
    for ip_permission in expected_ip_permissions:
        sg01.ip_permissions.shouldnt.contain(ip_permission)

    sg01.authorize_egress(IpPermissions=ip_permissions)
    sg01.ip_permissions_egress.should.have.length_of(6)
    for ip_permission in expected_ip_permissions:
        sg01.ip_permissions_egress.should.contain(ip_permission)

    sg01.revoke_egress(IpPermissions=ip_permissions)
    sg01.ip_permissions_egress.should.have.length_of(1)
    for ip_permission in expected_ip_permissions:
        sg01.ip_permissions_egress.shouldnt.contain(ip_permission)


@mock_ec2
def test_security_group_ingress_without_multirule():
    ec2 = boto3.resource("ec2", "ca-central-1")
    sg = ec2.create_security_group(Description="Test SG", GroupName="test-sg")

    assert len(sg.ip_permissions) == 0
    sg.authorize_ingress(
        CidrIp="192.168.0.1/32", FromPort=22, ToPort=22, IpProtocol="tcp"
    )

    # Fails
    assert len(sg.ip_permissions) == 1


@mock_ec2
def test_security_group_ingress_without_multirule_after_reload():
    ec2 = boto3.resource("ec2", "ca-central-1")
    sg = ec2.create_security_group(Description="Test SG", GroupName="test-sg")

    assert len(sg.ip_permissions) == 0
    sg.authorize_ingress(
        CidrIp="192.168.0.1/32", FromPort=22, ToPort=22, IpProtocol="tcp"
    )

    # Also Fails
    sg_after = ec2.SecurityGroup(sg.id)
    assert len(sg_after.ip_permissions) == 1


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
def test_revoke_security_group_egress():
    ec2 = boto3.resource("ec2", "us-east-1")
    sg = ec2.create_security_group(Description="Test SG", GroupName="test-sg")

    sg.ip_permissions_egress.should.equal(
        [
            {
                "IpProtocol": "-1",
                "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                "UserIdGroupPairs": [],
            }
        ]
    )

    sg.revoke_egress(
        IpPermissions=[
            {
                "IpProtocol": "-1",
                "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                "UserIdGroupPairs": [],
            }
        ]
    )

    sg.reload()
    sg.ip_permissions_egress.should.have.length_of(0)
