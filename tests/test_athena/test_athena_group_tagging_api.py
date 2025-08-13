import boto3
import pytest

from moto import mock_aws


@pytest.fixture(name="client")
@mock_aws
def get_client():
    return boto3.client("athena", region_name="us-east-1")


@pytest.fixture(name="resource_groups_client")
@mock_aws
def get_resource_groups_client():
    return boto3.client("resourcegroupstaggingapi", region_name="us-east-1")


@mock_aws
def test_athena_capacity_reservation_group_tagging_api(client, resource_groups_client):
    capacity_reservation_name = "athena_workgroup"
    tags = [{"Key": "key1", "Value": "value1"}, {"Key": "key2", "Value": "value2"}]
    capacity_reservation = client.create_capacity_reservation(
        TargetDpus=123,
        Name=capacity_reservation_name,
        Tags=tags,
    )
    metadata = capacity_reservation["ResponseMetadata"]
    assert metadata["HTTPStatusCode"] == 200
    assert metadata["RetryAttempts"] == 0

    resource_group_tags = resource_groups_client.get_resources(
        ResourceARNList=[capacity_reservation_name],
    )["ResourceTagMappingList"]
    assert len(resource_group_tags) == 1
    assert resource_group_tags[0]["ResourceARN"] == capacity_reservation_name
    assert resource_group_tags[0]["Tags"] == tags


@mock_aws
def test_create_work_group_group_tagging_api(client, resource_groups_client):
    work_group_name = "athena_workgroup"
    tags = [{"Key": "key1", "Value": "value1"}, {"Key": "key2", "Value": "value2"}]
    work_group = client.create_work_group(
        Name=work_group_name,
        Description="Test work group",
        Configuration={
            "ResultConfiguration": {
                "OutputLocation": "s3://bucket-name/prefix/",
                "EncryptionConfiguration": {
                    "EncryptionOption": "SSE_KMS",
                    "KmsKey": "aws:arn:kms:1233456789:us-east-1:key/number-1",
                },
            }
        },
        Tags=tags,
    )

    metadata = work_group["ResponseMetadata"]
    assert metadata["HTTPStatusCode"] == 200
    assert metadata["RetryAttempts"] == 0

    resource_group_tags = resource_groups_client.get_resources(
        ResourceARNList=[work_group_name],
    )["ResourceTagMappingList"]
    assert len(resource_group_tags) == 1
    assert resource_group_tags[0]["ResourceARN"] == work_group_name
    assert resource_group_tags[0]["Tags"] == tags


@mock_aws
def test_create_data_catalog_group_tagging_api(client, resource_groups_client):
    data_catalog_name = "data_catalog"
    tags = [{"Key": "key1", "Value": "value1"}, {"Key": "key2", "Value": "value2"}]
    data_catalog = client.create_data_catalog(
        Name=data_catalog_name,
        Type="GLUE",
        Description="Test data catalog",
        Parameters={"catalog-id": "AWS Test account ID"},
        Tags=tags,
    )

    metadata = data_catalog["ResponseMetadata"]
    assert metadata["HTTPStatusCode"] == 200
    assert metadata["RetryAttempts"] == 0

    resource_group_tags = resource_groups_client.get_resources(
        ResourceARNList=[data_catalog_name],
    )["ResourceTagMappingList"]
    assert len(resource_group_tags) == 1
    assert resource_group_tags[0]["ResourceARN"] == data_catalog_name
    assert resource_group_tags[0]["Tags"] == tags
