import boto3
import pytest

from moto import mock_aws


@pytest.fixture(name="client")
@mock_aws
def get_client():
    return boto3.client("servicecatalog", region_name="us-east-1")


@pytest.fixture(name="resource_groups_client")
@mock_aws
def get_resource_groups_client():
    return boto3.client("resourcegroupstaggingapi", region_name="us-east-1")


@mock_aws
def test_servicetatalog_portfolio_service_tagging_api(client, resource_groups_client):
    tags = [
        {"Key": "Moto", "Value": "Hello"},
        {"Key": "Environment", "Value": "Dev"},
    ]
    resp = client.create_portfolio(
        DisplayName="Test Portfolio",
        Description="Test Portfolio Description",
        ProviderName="Test Provider",
        Tags=tags,
        IdempotencyToken="test-token",
    )

    metadata = resp["ResponseMetadata"]
    assert metadata["HTTPStatusCode"] == 200
    assert metadata["RetryAttempts"] == 0

    portfolio = resp["PortfolioDetail"]
    resource_group_tags = resource_groups_client.get_resources(
        ResourceARNList=[portfolio["ARN"]],
    )["ResourceTagMappingList"]
    assert len(resource_group_tags) == 1
    assert resource_group_tags[0]["ResourceARN"] == portfolio["ARN"]
    assert resource_group_tags[0]["Tags"] == tags


@mock_aws
def test_servicetatalog_product_tagging_api(client, resource_groups_client):
    tags = [
        {"Key": "Moto", "Value": "Hello"},
        {"Key": "Environment", "Value": "Dev"},
    ]
    resp = client.create_product(
        Name="Test Product",
        Owner="Test Owner",
        ProductType="CLOUD_FORMATION_TEMPLATE",
        Tags=tags,
    )

    metadata = resp["ResponseMetadata"]
    assert metadata["HTTPStatusCode"] == 200
    assert metadata["RetryAttempts"] == 0

    product = resp["ProductViewDetail"]
    resource_group_tags = resource_groups_client.get_resources(
        ResourceARNList=[product["ProductARN"]],
    )["ResourceTagMappingList"]
    assert len(resource_group_tags) == 1
    assert resource_group_tags[0]["ResourceARN"] == product["ProductARN"]
    assert resource_group_tags[0]["Tags"] == tags
