"""Unit tests for route53resolver-supported APIs."""

import boto3

from moto import mock_aws

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_aws
def test_create_resolver_query_log_config():
    client = boto3.client("route53resolver", region_name="us-east-1")

    response = client.create_resolver_query_log_config(
        Name="test-query-log-config",
        DestinationArn="arn:aws:s3:::test-bucket",
        CreatorRequestId="test-creator-request-id",
        Tags=[{"Key": "Environment", "Value": "Test"}],
    )

    assert "ResolverQueryLogConfig" in response
    config = response["ResolverQueryLogConfig"]

    assert config["Name"] == "test-query-log-config"
    assert config["DestinationArn"] == "arn:aws:s3:::test-bucket"
    assert config["CreatorRequestId"] == "test-creator-request-id"
    assert config["Status"] == "CREATED"
    assert config["ShareStatus"] == "NOT_SHARED"
    assert config["AssociationCount"] == 0
    assert "Id" in config
    assert "Arn" in config
    assert "OwnerId" in config
    assert "CreationTime" in config


@mock_aws
def test_associate_resolver_query_log_config():
    ec2_client = boto3.client("ec2", region_name="us-east-1")

    vpc_response = ec2_client.create_vpc(CidrBlock="10.0.0.0/16")
    vpc_id = vpc_response["Vpc"]["VpcId"]

    client = boto3.client("route53resolver", region_name="us-east-1")

    config_response = client.create_resolver_query_log_config(
        Name="test-query-log-config",
        DestinationArn="arn:aws:s3:::test-bucket",
        CreatorRequestId="test-creator-request-id",
    )
    config_id = config_response["ResolverQueryLogConfig"]["Id"]

    associate_response = client.associate_resolver_query_log_config(
        ResolverQueryLogConfigId=config_id, ResourceId=vpc_id
    )

    assert "ResolverQueryLogConfigAssociation" in associate_response
    association = associate_response["ResolverQueryLogConfigAssociation"]

    assert association["ResolverQueryLogConfigId"] == config_id
    assert association["ResourceId"] == vpc_id
    assert association["Status"] == "ACTIVE"
    assert association["Error"] == "NONE"
    assert association["ErrorMessage"] == ""
    assert "Id" in association
    assert "CreationTime" in association

    get_config_response = client.get_resolver_query_log_config(
        ResolverQueryLogConfigId=config_id
    )
    assert get_config_response["ResolverQueryLogConfig"]["AssociationCount"] == 1


@mock_aws
def test_associate_resolver_query_log_config_with_nonexistent_vpc():
    client = boto3.client("route53resolver", region_name="us-east-1")

    config_response = client.create_resolver_query_log_config(
        Name="test-query-log-config",
        DestinationArn="arn:aws:s3:::test-bucket",
        CreatorRequestId="test-creator-request-id",
    )
    config_id = config_response["ResolverQueryLogConfig"]["Id"]

    try:
        client.associate_resolver_query_log_config(
            ResolverQueryLogConfigId=config_id, ResourceId="vpc-nonexistent"
        )
        assert False, (
            "Expected an InvalidParameterException but no exception was raised"
        )
    except client.exceptions.InvalidParameterException as e:
        assert "vpc ID 'vpc-nonexistent' does not exist" in str(e)


@mock_aws
def test_associate_resolver_query_log_config_with_nonexistent_config():
    ec2_client = boto3.client("ec2", region_name="us-east-1")

    vpc_response = ec2_client.create_vpc(CidrBlock="10.0.0.0/16")
    vpc_id = vpc_response["Vpc"]["VpcId"]

    client = boto3.client("route53resolver", region_name="us-east-1")

    nonexistent_config_id = "rslvr-qlc-nonexistent"
    try:
        client.associate_resolver_query_log_config(
            ResolverQueryLogConfigId=nonexistent_config_id, ResourceId=vpc_id
        )
        assert False, "Expected a ResourceNotFoundException but no exception was raised"
    except client.exceptions.ResourceNotFoundException as e:
        assert (
            f"Resolver query log config with ID '{nonexistent_config_id}' does not exist"
            in str(e)
        )


@mock_aws
def test_get_resolver_query_log_config():
    client = boto3.client("route53resolver", region_name="us-east-1")

    config_response = client.create_resolver_query_log_config(
        Name="test-query-log-config",
        DestinationArn="arn:aws:s3:::test-bucket",
        CreatorRequestId="test-creator-request-id",
        Tags=[{"Key": "Environment", "Value": "Test"}],
    )
    config_id = config_response["ResolverQueryLogConfig"]["Id"]

    get_response = client.get_resolver_query_log_config(
        ResolverQueryLogConfigId=config_id
    )

    assert "ResolverQueryLogConfig" in get_response
    config = get_response["ResolverQueryLogConfig"]

    assert config["Id"] == config_id
    assert config["Name"] == "test-query-log-config"
    assert config["DestinationArn"] == "arn:aws:s3:::test-bucket"
    assert config["CreatorRequestId"] == "test-creator-request-id"
    assert config["Status"] == "CREATED"
    assert config["ShareStatus"] == "NOT_SHARED"
    assert config["AssociationCount"] == 0
    assert "Arn" in config
    assert "OwnerId" in config
    assert "CreationTime" in config


@mock_aws
def test_get_nonexistent_resolver_query_log_config():
    client = boto3.client("route53resolver", region_name="us-east-1")

    nonexistent_config_id = "rslvr-qlc-nonexistent"
    try:
        client.get_resolver_query_log_config(
            ResolverQueryLogConfigId=nonexistent_config_id
        )
        assert False, "Expected a ResourceNotFoundException but no exception was raised"
    except client.exceptions.ResourceNotFoundException as e:
        assert (
            f"Resolver query log config with ID '{nonexistent_config_id}' does not exist"
            in str(e)
        )
