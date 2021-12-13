from __future__ import unicode_literals

from botocore.exceptions import ClientError
import boto3
import sure
from . import mock_rds


@mock_rds
def test_create_database_security_group():
    conn = boto3.client("rds", region_name="us-west-2")

    result = conn.create_db_security_group(
        DBSecurityGroupName="db_sg", DBSecurityGroupDescription="DB Security Group"
    )
    result["DBSecurityGroup"]["DBSecurityGroupName"].should.equal("db_sg")
    result["DBSecurityGroup"]["DBSecurityGroupDescription"].should.equal(
        "DB Security Group"
    )
    result["DBSecurityGroup"]["IPRanges"].should.equal([])


@mock_rds
def test_get_security_groups():
    conn = boto3.client("rds", region_name="us-west-2")

    result = conn.describe_db_security_groups()
    result["DBSecurityGroups"].should.have.length_of(0)

    conn.create_db_security_group(
        DBSecurityGroupName="db_sg1", DBSecurityGroupDescription="DB Security Group"
    )
    conn.create_db_security_group(
        DBSecurityGroupName="db_sg2", DBSecurityGroupDescription="DB Security Group"
    )

    result = conn.describe_db_security_groups()
    result["DBSecurityGroups"].should.have.length_of(2)

    result = conn.describe_db_security_groups(DBSecurityGroupName="db_sg1")
    result["DBSecurityGroups"].should.have.length_of(1)
    result["DBSecurityGroups"][0]["DBSecurityGroupName"].should.equal("db_sg1")


@mock_rds
def test_get_non_existent_security_group():
    conn = boto3.client("rds", region_name="us-west-2")
    conn.describe_db_security_groups.when.called_with(
        DBSecurityGroupName="not-a-sg"
    ).should.throw(ClientError)


@mock_rds
def test_delete_database_security_group():
    conn = boto3.client("rds", region_name="us-west-2")
    conn.create_db_security_group(
        DBSecurityGroupName="db_sg", DBSecurityGroupDescription="DB Security Group"
    )

    result = conn.describe_db_security_groups()
    result["DBSecurityGroups"].should.have.length_of(1)

    conn.delete_db_security_group(DBSecurityGroupName="db_sg")
    result = conn.describe_db_security_groups()
    result["DBSecurityGroups"].should.have.length_of(0)


@mock_rds
def test_delete_non_existent_security_group():
    conn = boto3.client("rds", region_name="us-west-2")
    conn.delete_db_security_group.when.called_with(
        DBSecurityGroupName="not-a-db"
    ).should.throw(ClientError)


@mock_rds
def test_security_group_authorize():
    conn = boto3.client("rds", region_name="us-west-2")
    security_group = conn.create_db_security_group(
        DBSecurityGroupName="db_sg", DBSecurityGroupDescription="DB Security Group"
    )
    security_group["DBSecurityGroup"]["IPRanges"].should.equal([])

    conn.authorize_db_security_group_ingress(
        DBSecurityGroupName="db_sg", CIDRIP="10.3.2.45/32"
    )

    result = conn.describe_db_security_groups(DBSecurityGroupName="db_sg")
    result["DBSecurityGroups"][0]["IPRanges"].should.have.length_of(1)
    result["DBSecurityGroups"][0]["IPRanges"].should.equal(
        [{"Status": "authorized", "CIDRIP": "10.3.2.45/32"}]
    )

    conn.authorize_db_security_group_ingress(
        DBSecurityGroupName="db_sg", CIDRIP="10.3.2.46/32"
    )
    result = conn.describe_db_security_groups(DBSecurityGroupName="db_sg")
    result["DBSecurityGroups"][0]["IPRanges"].should.have.length_of(2)
    result["DBSecurityGroups"][0]["IPRanges"].should.equal(
        [
            {"Status": "authorized", "CIDRIP": "10.3.2.45/32"},
            {"Status": "authorized", "CIDRIP": "10.3.2.46/32"},
        ]
    )


@mock_rds
def test_add_security_group_to_database():
    conn = boto3.client("rds", region_name="us-west-2")

    conn.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        AllocatedStorage=10,
        DBInstanceClass="db.m1.small",
        Engine="postgres",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
    )

    result = conn.describe_db_instances()
    result["DBInstances"][0]["DBSecurityGroups"].should.equal([])
    conn.create_db_security_group(
        DBSecurityGroupName="db_sg", DBSecurityGroupDescription="DB Security Group"
    )
    conn.modify_db_instance(
        DBInstanceIdentifier="db-master-1", DBSecurityGroups=["db_sg"]
    )
    result = conn.describe_db_instances()
    result["DBInstances"][0]["DBSecurityGroups"][0]["DBSecurityGroupName"].should.equal(
        "db_sg"
    )


@mock_rds
def test_list_tags_security_group():
    test_tags = [
        {"Key": "foo", "Value": "bar",},
        {"Key": "foo1", "Value": "bar1",},
    ]
    conn = boto3.client("rds", region_name="us-west-2")
    security_group = conn.create_db_security_group(
        DBSecurityGroupName="db_sg",
        DBSecurityGroupDescription="DB Security Group",
        Tags=test_tags,
    ).get("DBSecurityGroup")
    result = conn.list_tags_for_resource(
        ResourceName=security_group["DBSecurityGroupArn"]
    )
    result["TagList"].should.equal(test_tags)


@mock_rds
def test_add_tags_security_group():
    conn = boto3.client("rds", region_name="us-west-2")
    result = conn.describe_db_subnet_groups()
    result["DBSubnetGroups"].should.have.length_of(0)

    security_group = conn.create_db_security_group(
        DBSecurityGroupName="db_sg", DBSecurityGroupDescription="DB Security Group"
    )["DBSecurityGroup"]["DBSecurityGroupName"]

    resource = "arn:aws:rds:us-west-2:1234567890:secgrp:{0}".format(security_group)
    conn.add_tags_to_resource(
        ResourceName=resource,
        Tags=[{"Value": "bar", "Key": "foo"}, {"Value": "bar1", "Key": "foo1"}],
    )

    result = conn.list_tags_for_resource(ResourceName=resource)
    result["TagList"].should.equal(
        [{"Value": "bar", "Key": "foo"}, {"Value": "bar1", "Key": "foo1"}]
    )


@mock_rds
def test_remove_tags_security_group():
    conn = boto3.client("rds", region_name="us-west-2")
    result = conn.describe_db_subnet_groups()
    result["DBSubnetGroups"].should.have.length_of(0)

    security_group = conn.create_db_security_group(
        DBSecurityGroupName="db_sg",
        DBSecurityGroupDescription="DB Security Group",
        Tags=[{"Value": "bar", "Key": "foo"}, {"Value": "bar1", "Key": "foo1"}],
    )["DBSecurityGroup"]["DBSecurityGroupName"]

    resource = "arn:aws:rds:us-west-2:1234567890:secgrp:{0}".format(security_group)
    conn.remove_tags_from_resource(ResourceName=resource, TagKeys=["foo"])

    result = conn.list_tags_for_resource(ResourceName=resource)
    result["TagList"].should.equal([{"Value": "bar1", "Key": "foo1"}])
