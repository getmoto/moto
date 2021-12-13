from __future__ import unicode_literals

from botocore.exceptions import ClientError, ParamValidationError
import boto3
import sure  # noqa
from . import mock_ec2, mock_kms, mock_rds
from sure import this


@mock_rds
def test_create_option_group():
    client = boto3.client("rds", region_name="us-west-2")
    option_group = client.create_option_group(
        OptionGroupName="test",
        EngineName="mysql",
        MajorEngineVersion="5.6",
        OptionGroupDescription="test option group",
    ).get("OptionGroup")
    option_group["OptionGroupName"].should.equal("test")
    option_group["EngineName"].should.equal("mysql")
    option_group["OptionGroupDescription"].should.equal("test option group")
    option_group["MajorEngineVersion"].should.equal("5.6")


@mock_rds
def test_create_option_group_bad_engine_name():
    conn = boto3.client("rds", region_name="us-west-2")
    conn.create_option_group.when.called_with(
        OptionGroupName="test",
        EngineName="invalid_engine",
        MajorEngineVersion="5.6",
        OptionGroupDescription="test invalid engine",
    ).should.throw(ClientError)


@mock_rds
def test_create_option_group_bad_engine_major_version():
    conn = boto3.client("rds", region_name="us-west-2")
    conn.create_option_group.when.called_with(
        OptionGroupName="test",
        EngineName="mysql",
        MajorEngineVersion="6.6.6",
        OptionGroupDescription="test invalid engine version",
    ).should.throw(ClientError)


@mock_rds
def test_create_option_group_empty_description():
    conn = boto3.client("rds", region_name="us-west-2")
    conn.create_option_group.when.called_with(
        OptionGroupName="test",
        EngineName="mysql",
        MajorEngineVersion="5.6",
        OptionGroupDescription="",
    ).should.throw(ClientError)


@mock_rds
def test_create_option_group_duplicate():
    conn = boto3.client("rds", region_name="us-west-2")
    conn.create_option_group(
        OptionGroupName="test",
        EngineName="mysql",
        MajorEngineVersion="5.6",
        OptionGroupDescription="test option group",
    )
    conn.create_option_group.when.called_with(
        OptionGroupName="test",
        EngineName="mysql",
        MajorEngineVersion="5.6",
        OptionGroupDescription="test option group",
    ).should.throw(ClientError)


@mock_rds
def test_describe_option_group():
    conn = boto3.client("rds", region_name="us-west-2")
    conn.create_option_group(
        OptionGroupName="test",
        EngineName="mysql",
        MajorEngineVersion="5.6",
        OptionGroupDescription="test option group",
    )
    option_groups = conn.describe_option_groups(OptionGroupName="test")
    option_groups["OptionGroupsList"][0]["OptionGroupName"].should.equal("test")


@mock_rds
def test_describe_non_existant_option_group():
    conn = boto3.client("rds", region_name="us-west-2")
    conn.describe_option_groups.when.called_with(
        OptionGroupName="not-a-option-group"
    ).should.throw(ClientError)


@mock_rds
def test_delete_option_group():
    conn = boto3.client("rds", region_name="us-west-2")
    conn.create_option_group(
        OptionGroupName="test",
        EngineName="mysql",
        MajorEngineVersion="5.6",
        OptionGroupDescription="test option group",
    )
    option_groups = conn.describe_option_groups(OptionGroupName="test")
    option_groups["OptionGroupsList"][0]["OptionGroupName"].should.equal("test")
    conn.delete_option_group(OptionGroupName="test")
    conn.describe_option_groups.when.called_with(OptionGroupName="test").should.throw(
        ClientError
    )


@mock_rds
def test_delete_non_existant_option_group():
    conn = boto3.client("rds", region_name="us-west-2")
    conn.delete_option_group.when.called_with(
        OptionGroupName="non-existant"
    ).should.throw(ClientError)


@mock_rds
def test_describe_option_group_options():
    client = boto3.client("rds", region_name="us-west-2")
    option_group_options = client.describe_option_group_options(
        EngineName="sqlserver-ee"
    ).get("OptionGroupOptions")
    this(len(option_group_options)).should.be.greater_than(0)
    option_group_options = client.describe_option_group_options(
        EngineName="sqlserver-ee", MajorEngineVersion="11.00"
    ).get("OptionGroupOptions")
    this(len(option_group_options)).should.be.greater_than(0)
    option_group_options = client.describe_option_group_options(
        EngineName="mysql", MajorEngineVersion="5.6"
    ).get("OptionGroupOptions")
    this(len(option_group_options)).should.be.greater_than(0)
    client.describe_option_group_options.when.called_with(
        EngineName="non-existent"
    ).should.throw(ClientError, "Invalid DB engine")
    client.describe_option_group_options.when.called_with(
        EngineName="mysql", MajorEngineVersion="non-existent"
    ).should.throw(ClientError, "Cannot find major version non-existent for mysql")

    option_group_options = client.describe_option_group_options(
        EngineName="oracle-ee", MajorEngineVersion="12.1"
    ).get("OptionGroupOptions")
    this(len(option_group_options)).should.be.greater_than(0)


@mock_rds
def test_describe_option_group_options_paginated():
    client = boto3.client("rds", region_name="us-west-2")

    client.describe_option_group_options.when.called_with(
        EngineName="oracle-se", MaxRecords=0
    ).should.throw(ClientError, "Invalid value 0 for MaxRecords")

    client.describe_option_group_options.when.called_with(
        EngineName="oracle-se", MaxRecords=101
    ).should.throw(ClientError, "Invalid value 101 for MaxRecords")

    resp = client.describe_option_group_options(EngineName="oracle-se", MaxRecords=20)
    resp["OptionGroupOptions"].should.have.length_of(20)

    resp2 = client.describe_option_group_options(
        EngineName="oracle-se", Marker=resp["Marker"]
    )
    resp2["OptionGroupOptions"].should.have.length_of(3)

    resp3 = client.describe_option_group_options(EngineName="oracle-se")
    resp3["OptionGroupOptions"].should.have.length_of(23)


@mock_rds
def test_modify_option_group():
    conn = boto3.client("rds", region_name="us-west-2")
    conn.create_option_group(
        OptionGroupName="test",
        EngineName="mysql",
        MajorEngineVersion="5.6",
        OptionGroupDescription="test option group",
    )
    # TODO: create option and validate before deleting.
    # if Someone can tell me how the hell to use this function
    # to add options to an option_group, I can finish coding this.
    result = conn.modify_option_group(
        OptionGroupName="test",
        OptionsToInclude=[],
        OptionsToRemove=["MEMCACHED"],
        ApplyImmediately=True,
    )
    result["OptionGroup"]["EngineName"].should.equal("mysql")
    result["OptionGroup"]["Options"].should.equal([])
    result["OptionGroup"]["OptionGroupName"].should.equal("test")


@mock_rds
def test_modify_option_group_no_options():
    conn = boto3.client("rds", region_name="us-west-2")
    conn.create_option_group(
        OptionGroupName="test",
        EngineName="mysql",
        MajorEngineVersion="5.6",
        OptionGroupDescription="test option group",
    )
    conn.modify_option_group.when.called_with(OptionGroupName="test").should.throw(
        ClientError
    )


@mock_rds
def test_modify_non_existant_option_group():
    conn = boto3.client("rds", region_name="us-west-2")
    conn.modify_option_group.when.called_with(
        OptionGroupName="non-existant",
        OptionsToInclude=[
            (
                "OptionName",
                "Port",
                "DBSecurityGroupMemberships",
                "VpcSecurityGroupMemberships",
                "OptionSettings",
            )
        ],
    ).should.throw(ParamValidationError)


@mock_rds
def test_add_tags_option_group():
    conn = boto3.client("rds", region_name="us-west-2")
    conn.create_option_group(
        OptionGroupName="test",
        EngineName="mysql",
        MajorEngineVersion="5.6",
        OptionGroupDescription="test option group",
    )
    result = conn.list_tags_for_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:og:test"
    )
    list(result["TagList"]).should.have.length_of(0)
    conn.add_tags_to_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:og:test",
        Tags=[{"Key": "foo", "Value": "fish",}, {"Key": "foo2", "Value": "bar2",}],
    )
    result = conn.list_tags_for_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:og:test"
    )
    list(result["TagList"]).should.have.length_of(2)


@mock_rds
def test_remove_tags_option_group():
    conn = boto3.client("rds", region_name="us-west-2")
    conn.create_option_group(
        OptionGroupName="test",
        EngineName="mysql",
        MajorEngineVersion="5.6",
        OptionGroupDescription="test option group",
    )
    result = conn.list_tags_for_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:og:test"
    )
    conn.add_tags_to_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:og:test",
        Tags=[{"Key": "foo", "Value": "fish",}, {"Key": "foo2", "Value": "bar2",}],
    )
    result = conn.list_tags_for_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:og:test"
    )
    list(result["TagList"]).should.have.length_of(2)
    conn.remove_tags_from_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:og:test", TagKeys=["foo"]
    )
    result = conn.list_tags_for_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:og:test"
    )
    list(result["TagList"]).should.have.length_of(1)
