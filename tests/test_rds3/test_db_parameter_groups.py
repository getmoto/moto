from __future__ import unicode_literals

import boto3
from botocore.exceptions import ClientError
from sure import this

from . import mock_rds


@mock_rds
def test_create_db_parameter_group():
    conn = boto3.client("rds", region_name="us-west-2")
    db_parameter_group = conn.create_db_parameter_group(
        DBParameterGroupName="test",
        DBParameterGroupFamily="mysql5.6",
        Description="test parameter group",
    )

    db_parameter_group["DBParameterGroup"]["DBParameterGroupName"].should.equal("test")
    db_parameter_group["DBParameterGroup"]["DBParameterGroupFamily"].should.equal(
        "mysql5.6"
    )
    db_parameter_group["DBParameterGroup"]["Description"].should.equal(
        "test parameter group"
    )


@mock_rds
def test_create_db_instance_with_parameter_group():
    conn = boto3.client("rds", region_name="us-west-2")
    conn.create_db_parameter_group(
        DBParameterGroupName="test",
        DBParameterGroupFamily="mysql5.6",
        Description="test parameter group",
    )

    database = conn.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        AllocatedStorage=10,
        Engine="mysql",
        DBInstanceClass="db.m1.small",
        DBParameterGroupName="test",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
    )

    this(len(database["DBInstance"]["DBParameterGroups"])).should.equal(1)
    database["DBInstance"]["DBParameterGroups"][0]["DBParameterGroupName"].should.equal(
        "test"
    )
    database["DBInstance"]["DBParameterGroups"][0]["ParameterApplyStatus"].should.equal(
        "in-sync"
    )


@mock_rds
def test_modify_db_instance_with_parameter_group():
    conn = boto3.client("rds", region_name="us-west-2")
    database = conn.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        AllocatedStorage=10,
        Engine="mysql",
        DBInstanceClass="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
    )

    this(len(database["DBInstance"]["DBParameterGroups"])).should.equal(1)
    database["DBInstance"]["DBParameterGroups"][0]["DBParameterGroupName"].should.equal(
        "default.mysql5.6"
    )
    database["DBInstance"]["DBParameterGroups"][0]["ParameterApplyStatus"].should.equal(
        "in-sync"
    )

    conn.create_db_parameter_group(
        DBParameterGroupName="test",
        DBParameterGroupFamily="mysql5.6",
        Description="test parameter group",
    )
    conn.modify_db_instance(
        DBInstanceIdentifier="db-master-1",
        DBParameterGroupName="test",
        ApplyImmediately=True,
    )

    database = conn.describe_db_instances(DBInstanceIdentifier="db-master-1")[
        "DBInstances"
    ][0]
    this(len(database["DBParameterGroups"])).should.equal(1)
    database["DBParameterGroups"][0]["DBParameterGroupName"].should.equal("test")
    database["DBParameterGroups"][0]["ParameterApplyStatus"].should.equal(
        "pending-reboot"
    )


@mock_rds
def test_create_db_parameter_group_empty_description():
    conn = boto3.client("rds", region_name="us-west-2")
    conn.create_db_parameter_group.when.called_with(
        DBParameterGroupName="test", DBParameterGroupFamily="mysql5.6", Description=""
    ).should.throw(ClientError)


@mock_rds
def test_create_db_parameter_group_duplicate():
    conn = boto3.client("rds", region_name="us-west-2")
    conn.create_db_parameter_group(
        DBParameterGroupName="test",
        DBParameterGroupFamily="mysql5.6",
        Description="test parameter group",
    )
    conn.create_db_parameter_group.when.called_with(
        DBParameterGroupName="test",
        DBParameterGroupFamily="mysql5.6",
        Description="test parameter group",
    ).should.throw(ClientError)


@mock_rds
def test_describe_db_parameter_group():
    conn = boto3.client("rds", region_name="us-west-2")
    conn.create_db_parameter_group(
        DBParameterGroupName="test",
        DBParameterGroupFamily="mysql5.6",
        Description="test parameter group",
    )
    conn.create_db_parameter_group(
        DBParameterGroupName="test2",
        DBParameterGroupFamily="mysql5.6",
        Description="test parameter group",
    )
    db_parameter_groups = conn.describe_db_parameter_groups(DBParameterGroupName="test")
    db_parameter_groups["DBParameterGroups"][0]["DBParameterGroupName"].should.equal(
        "test"
    )


@mock_rds
def test_describe_non_existent_db_parameter_group():
    conn = boto3.client("rds", region_name="us-west-2")
    conn.describe_db_parameter_groups.when.called_with(
        DBParameterGroupName="test"
    ).should.throw(ClientError, "DBParameterGroup not found: test")


@mock_rds
def test_delete_db_parameter_group():
    conn = boto3.client("rds", region_name="us-west-2")
    conn.create_db_parameter_group(
        DBParameterGroupName="test",
        DBParameterGroupFamily="mysql5.6",
        Description="test parameter group",
    )
    db_parameter_groups = conn.describe_db_parameter_groups(DBParameterGroupName="test")
    db_parameter_groups["DBParameterGroups"][0]["DBParameterGroupName"].should.equal(
        "test"
    )
    conn.delete_db_parameter_group(DBParameterGroupName="test")
    conn.describe_db_parameter_groups.when.called_with(
        DBParameterGroupName="test"
    ).should.throw(ClientError, "DBParameterGroup not found: test")


@mock_rds
def test_modify_db_parameter_group():
    conn = boto3.client("rds", region_name="us-west-2")
    conn.create_db_parameter_group(
        DBParameterGroupName="test",
        DBParameterGroupFamily="mysql5.6",
        Description="test parameter group",
    )

    modify_result = conn.modify_db_parameter_group(
        DBParameterGroupName="test",
        Parameters=[
            {
                "ParameterName": "foo",
                "ParameterValue": "foo_val",
                "Description": "test param",
                "ApplyMethod": "immediate",
            }
        ],
    )

    modify_result["DBParameterGroupName"].should.equal("test")

    db_parameters = conn.describe_db_parameters(DBParameterGroupName="test")
    db_parameters["Parameters"][0]["ParameterName"].should.equal("foo")
    db_parameters["Parameters"][0]["ParameterValue"].should.equal("foo_val")
    db_parameters["Parameters"][0]["Description"].should.equal("test param")
    db_parameters["Parameters"][0]["ApplyMethod"].should.equal("immediate")


@mock_rds
def test_delete_non_existent_db_parameter_group():
    conn = boto3.client("rds", region_name="us-west-2")
    conn.delete_db_parameter_group.when.called_with(
        DBParameterGroupName="non-existent"
    ).should.throw(ClientError)


@mock_rds
def test_create_parameter_group_with_tags():
    test_tags = [
        {"Key": "foo", "Value": "bar",},
        {"Key": "foo1", "Value": "bar1",},
    ]
    conn = boto3.client("rds", region_name="us-west-2")
    conn.create_db_parameter_group(
        DBParameterGroupName="test",
        DBParameterGroupFamily="mysql5.6",
        Description="test parameter group",
        Tags=test_tags,
    )
    param_group = conn.describe_db_parameter_groups(DBParameterGroupName="test").get(
        "DBParameterGroups"
    )[0]
    result = conn.list_tags_for_resource(
        ResourceName=param_group["DBParameterGroupArn"]
    )
    result["TagList"].should.equal(test_tags)
