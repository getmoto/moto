"""Unit tests for route53resolver-supported APIs."""

import boto3
import pytest
from botocore.exceptions import ClientError

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

    with pytest.raises(ClientError) as exc:
        client.associate_resolver_query_log_config(
            ResolverQueryLogConfigId=config_id, ResourceId="vpc-nonexistent"
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterException"
    assert err["Message"] == "The vpc ID 'vpc-nonexistent' does not exist"


@mock_aws
def test_associate_resolver_query_log_config_with_nonexistent_config():
    ec2_client = boto3.client("ec2", region_name="us-east-1")

    vpc_response = ec2_client.create_vpc(CidrBlock="10.0.0.0/16")
    vpc_id = vpc_response["Vpc"]["VpcId"]

    client = boto3.client("route53resolver", region_name="us-east-1")

    nonexistent_config_id = "rslvr-qlc-nonexistent"
    with pytest.raises(ClientError) as exc:
        client.associate_resolver_query_log_config(
            ResolverQueryLogConfigId=nonexistent_config_id, ResourceId=vpc_id
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert (
        err["Message"]
        == f"Resolver query log config with ID '{nonexistent_config_id}' does not exist"
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
    with pytest.raises(ClientError) as exc:
        client.get_resolver_query_log_config(
            ResolverQueryLogConfigId=nonexistent_config_id
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert (
        err["Message"]
        == f"Resolver query log config with ID '{nonexistent_config_id}' does not exist"
    )


@mock_aws
def test_list_resolver_query_log_configs():
    client = boto3.client("route53resolver", region_name="us-east-1")

    config_ids = []
    for i in range(3):
        response = client.create_resolver_query_log_config(
            Name=f"test-query-log-config-{i}",
            DestinationArn=f"arn:aws:s3:::test-bucket-{i}",
            CreatorRequestId=f"test-creator-request-id-{i}",
        )
        config_ids.append(response["ResolverQueryLogConfig"]["Id"])

    response = client.list_resolver_query_log_configs()

    assert "ResolverQueryLogConfigs" in response
    assert len(response["ResolverQueryLogConfigs"]) == 3
    assert response["TotalCount"] == 3
    assert response["TotalFilteredCount"] == 3

    returned_ids = [c["Id"] for c in response["ResolverQueryLogConfigs"]]
    for config_id in config_ids:
        assert config_id in returned_ids


@mock_aws
def test_list_resolver_query_log_configs_with_filters():
    client = boto3.client("route53resolver", region_name="us-east-1")

    client.create_resolver_query_log_config(
        Name="production-logs",
        DestinationArn="arn:aws:s3:::prod-bucket",
        CreatorRequestId="prod-request-id",
    )
    client.create_resolver_query_log_config(
        Name="staging-logs",
        DestinationArn="arn:aws:s3:::staging-bucket",
        CreatorRequestId="staging-request-id",
    )

    response = client.list_resolver_query_log_configs(
        Filters=[{"Name": "Name", "Values": ["production-logs"]}]
    )

    assert len(response["ResolverQueryLogConfigs"]) == 1
    assert response["ResolverQueryLogConfigs"][0]["Name"] == "production-logs"


@mock_aws
def test_list_resolver_query_log_configs_empty():
    client = boto3.client("route53resolver", region_name="us-east-1")

    response = client.list_resolver_query_log_configs()

    assert "ResolverQueryLogConfigs" in response
    assert len(response["ResolverQueryLogConfigs"]) == 0
    assert response["TotalCount"] == 0


@mock_aws
def test_get_resolver_query_log_config_association():
    ec2_client = boto3.client("ec2", region_name="us-east-1")
    client = boto3.client("route53resolver", region_name="us-east-1")

    vpc_response = ec2_client.create_vpc(CidrBlock="10.0.0.0/16")
    vpc_id = vpc_response["Vpc"]["VpcId"]

    config_response = client.create_resolver_query_log_config(
        Name="test-query-log-config",
        DestinationArn="arn:aws:s3:::test-bucket",
        CreatorRequestId="test-creator-request-id",
    )
    config_id = config_response["ResolverQueryLogConfig"]["Id"]

    assoc_response = client.associate_resolver_query_log_config(
        ResolverQueryLogConfigId=config_id, ResourceId=vpc_id
    )
    association_id = assoc_response["ResolverQueryLogConfigAssociation"]["Id"]

    get_response = client.get_resolver_query_log_config_association(
        ResolverQueryLogConfigAssociationId=association_id
    )

    assert "ResolverQueryLogConfigAssociation" in get_response
    association = get_response["ResolverQueryLogConfigAssociation"]

    assert association["Id"] == association_id
    assert association["ResolverQueryLogConfigId"] == config_id
    assert association["ResourceId"] == vpc_id
    assert association["Status"] == "ACTIVE"
    assert association["Error"] == "NONE"
    assert association["ErrorMessage"] == ""
    assert "CreationTime" in association


@mock_aws
def test_get_nonexistent_resolver_query_log_config_association():
    client = boto3.client("route53resolver", region_name="us-east-1")

    nonexistent_association_id = "rslvr-qlcassoc-nonexistent"
    with pytest.raises(ClientError) as exc:
        client.get_resolver_query_log_config_association(
            ResolverQueryLogConfigAssociationId=nonexistent_association_id
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert (
        err["Message"]
        == f"Resolver query log config association with ID '{nonexistent_association_id}' does not exist"
    )


@mock_aws
def test_list_resolver_query_log_config_associations():
    ec2_client = boto3.client("ec2", region_name="us-east-1")
    client = boto3.client("route53resolver", region_name="us-east-1")

    vpc_ids = []
    for i in range(2):
        vpc_response = ec2_client.create_vpc(CidrBlock=f"10.{i}.0.0/16")
        vpc_ids.append(vpc_response["Vpc"]["VpcId"])

    config_response = client.create_resolver_query_log_config(
        Name="test-query-log-config",
        DestinationArn="arn:aws:s3:::test-bucket",
        CreatorRequestId="test-creator-request-id",
    )
    config_id = config_response["ResolverQueryLogConfig"]["Id"]

    association_ids = []
    for vpc_id in vpc_ids:
        assoc_response = client.associate_resolver_query_log_config(
            ResolverQueryLogConfigId=config_id, ResourceId=vpc_id
        )
        association_ids.append(
            assoc_response["ResolverQueryLogConfigAssociation"]["Id"]
        )

    response = client.list_resolver_query_log_config_associations()

    assert "ResolverQueryLogConfigAssociations" in response
    assert len(response["ResolverQueryLogConfigAssociations"]) == 2
    assert response["TotalCount"] == 2
    assert response["TotalFilteredCount"] == 2

    returned_ids = [a["Id"] for a in response["ResolverQueryLogConfigAssociations"]]
    for assoc_id in association_ids:
        assert assoc_id in returned_ids


@mock_aws
def test_list_resolver_query_log_config_associations_with_filters():
    ec2_client = boto3.client("ec2", region_name="us-east-1")
    client = boto3.client("route53resolver", region_name="us-east-1")

    vpc1 = ec2_client.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]["VpcId"]
    vpc2 = ec2_client.create_vpc(CidrBlock="10.1.0.0/16")["Vpc"]["VpcId"]

    config_response = client.create_resolver_query_log_config(
        Name="test-query-log-config",
        DestinationArn="arn:aws:s3:::test-bucket",
        CreatorRequestId="test-creator-request-id",
    )
    config_id = config_response["ResolverQueryLogConfig"]["Id"]

    client.associate_resolver_query_log_config(
        ResolverQueryLogConfigId=config_id, ResourceId=vpc1
    )
    client.associate_resolver_query_log_config(
        ResolverQueryLogConfigId=config_id, ResourceId=vpc2
    )

    response = client.list_resolver_query_log_config_associations(
        Filters=[{"Name": "ResourceId", "Values": [vpc1]}]
    )

    assert len(response["ResolverQueryLogConfigAssociations"]) == 1
    assert response["ResolverQueryLogConfigAssociations"][0]["ResourceId"] == vpc1


@mock_aws
def test_list_resolver_query_log_config_associations_empty():
    client = boto3.client("route53resolver", region_name="us-east-1")

    response = client.list_resolver_query_log_config_associations()

    assert "ResolverQueryLogConfigAssociations" in response
    assert len(response["ResolverQueryLogConfigAssociations"]) == 0
    assert response["TotalCount"] == 0


@mock_aws
def test_list_resolver_query_log_configs_pagination():
    client = boto3.client("route53resolver", region_name="us-east-1")

    for i in range(3):
        client.create_resolver_query_log_config(
            Name=f"test-config-{i}",
            DestinationArn=f"arn:aws:s3:::test-bucket-{i}",
            CreatorRequestId=f"creator-{i}",
        )

    response = client.list_resolver_query_log_configs(MaxResults=2)

    assert len(response["ResolverQueryLogConfigs"]) == 2
    assert "NextToken" in response

    response2 = client.list_resolver_query_log_configs(NextToken=response["NextToken"])

    assert len(response2["ResolverQueryLogConfigs"]) == 1
    assert "NextToken" not in response2


@mock_aws
def test_list_resolver_query_log_config_associations_pagination():
    ec2_client = boto3.client("ec2", region_name="us-east-1")
    client = boto3.client("route53resolver", region_name="us-east-1")

    vpc_ids = []
    for i in range(3):
        vpc_response = ec2_client.create_vpc(CidrBlock=f"10.{i}.0.0/16")
        vpc_ids.append(vpc_response["Vpc"]["VpcId"])

    config_response = client.create_resolver_query_log_config(
        Name="test-query-log-config",
        DestinationArn="arn:aws:s3:::test-bucket",
        CreatorRequestId="test-creator-request-id",
    )
    config_id = config_response["ResolverQueryLogConfig"]["Id"]

    for vpc_id in vpc_ids:
        client.associate_resolver_query_log_config(
            ResolverQueryLogConfigId=config_id, ResourceId=vpc_id
        )

    response = client.list_resolver_query_log_config_associations(MaxResults=2)

    assert len(response["ResolverQueryLogConfigAssociations"]) == 2
    assert "NextToken" in response

    response2 = client.list_resolver_query_log_config_associations(
        NextToken=response["NextToken"]
    )

    assert len(response2["ResolverQueryLogConfigAssociations"]) == 1
    assert "NextToken" not in response2
