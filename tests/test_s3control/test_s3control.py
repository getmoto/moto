import boto3
import pytest
from boto3 import Session
from botocore.client import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID


@mock_aws
def test_get_public_access_block_for_account():
    client = boto3.client("s3control", region_name="us-west-2")

    # With an invalid account ID:
    with pytest.raises(ClientError) as ce_err:
        client.get_public_access_block(AccountId="111111111111")
    assert ce_err.value.response["Error"]["Code"] == "AccessDenied"

    # Without one defined:
    with pytest.raises(ClientError) as ce_err:
        client.get_public_access_block(AccountId=ACCOUNT_ID)
    assert (
        ce_err.value.response["Error"]["Code"] == "NoSuchPublicAccessBlockConfiguration"
    )

    # Put a with an invalid account ID:
    with pytest.raises(ClientError) as ce_err:
        client.put_public_access_block(
            AccountId="111111111111",
            PublicAccessBlockConfiguration={"BlockPublicAcls": True},
        )
    assert ce_err.value.response["Error"]["Code"] == "AccessDenied"

    # Put with an invalid PAB:
    with pytest.raises(ClientError) as ce_err:
        client.put_public_access_block(
            AccountId=ACCOUNT_ID, PublicAccessBlockConfiguration={}
        )
    assert ce_err.value.response["Error"]["Code"] == "InvalidRequest"
    assert (
        "Must specify at least one configuration."
        in ce_err.value.response["Error"]["Message"]
    )

    # Correct PAB:
    client.put_public_access_block(
        AccountId=ACCOUNT_ID,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": True,
            "RestrictPublicBuckets": True,
        },
    )

    # Get the correct PAB (for all regions):
    for region in Session().get_available_regions("s3control"):
        region_client = boto3.client("s3control", region_name=region)
        assert region_client.get_public_access_block(AccountId=ACCOUNT_ID)[
            "PublicAccessBlockConfiguration"
        ] == {
            "BlockPublicAcls": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": True,
            "RestrictPublicBuckets": True,
        }

    # Delete with an invalid account ID:
    with pytest.raises(ClientError) as ce_err:
        client.delete_public_access_block(AccountId="111111111111")
    assert ce_err.value.response["Error"]["Code"] == "AccessDenied"

    # Delete successfully:
    client.delete_public_access_block(AccountId=ACCOUNT_ID)

    # Confirm that it's deleted:
    with pytest.raises(ClientError) as ce_err:
        client.get_public_access_block(AccountId=ACCOUNT_ID)
    assert (
        ce_err.value.response["Error"]["Code"] == "NoSuchPublicAccessBlockConfiguration"
    )


@mock_aws
def test_storage_lens_configuration():
    client = boto3.client("s3control", region_name="us-east-2")
    config_id = "my-test-config-id"
    config = {
        "Id": "id-test",
        "AccountLevel": {
            "ActivityMetrics": {"IsEnabled": True},
            "BucketLevel": {
                "ActivityMetrics": {"IsEnabled": True},
                "PrefixLevel": {
                    "StorageMetrics": {
                        "IsEnabled": True,
                        "SelectionCriteria": {
                            "Delimiter": "string",
                            "MaxDepth": 123,
                            "MinStorageBytesPercentage": 100,
                        },
                    }
                },
                "AdvancedCostOptimizationMetrics": {"IsEnabled": True},
                "AdvancedDataProtectionMetrics": {"IsEnabled": True},
                "DetailedStatusCodesMetrics": {"IsEnabled": True},
            },
            "AdvancedCostOptimizationMetrics": {"IsEnabled": True},
            "AdvancedDataProtectionMetrics": {"IsEnabled": True},
            "DetailedStatusCodesMetrics": {"IsEnabled": True},
            "StorageLensGroupLevel": {
                "SelectionCriteria": {
                    "Include": [
                        "string",
                    ],
                    "Exclude": [
                        "string",
                    ],
                }
            },
        },
        "Include": {
            "Buckets": [
                "string",
            ],
            "Regions": [
                "string",
            ],
        },
        "Exclude": {
            "Buckets": [
                "string",
            ],
            "Regions": [
                "string",
            ],
        },
        "DataExport": {
            "S3BucketDestination": {
                "Format": "CSV",
                "OutputSchemaVersion": "V_1",
                "AccountId": ACCOUNT_ID,
                "Arn": "arn:aws:s3:::bucket_name",
                "Prefix": "/prefix",
                "Encryption": {"SSES3": {}},
            },
            "CloudWatchMetrics": {"IsEnabled": True},
        },
        "IsEnabled": True,
        "AwsOrg": {"Arn": "string"},
        "StorageLensArn": "string",
    }
    tags = [
        {
            "Key": "string",
            "Value": "string",
        },
    ]

    resp = client.put_storage_lens_configuration(
        AccountId=ACCOUNT_ID,
        ConfigId=config_id,
        StorageLensConfiguration=config,
        Tags=tags,
    )
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    # Get the configuration:
    resp = client.get_storage_lens_configuration(
        AccountId=ACCOUNT_ID, ConfigId=config_id
    )
    assert "StorageLensConfiguration" in resp
    assert resp["StorageLensConfiguration"]["Id"] == "id-test"
    s3_dest = resp["StorageLensConfiguration"]["DataExport"]["S3BucketDestination"]
    assert s3_dest["AccountId"] == ACCOUNT_ID
    assert s3_dest["Arn"] == "arn:aws:s3:::bucket_name"
    assert "Encryption" in s3_dest
    assert s3_dest["Encryption"]["SSES3"] == {}

    # List the configurations
    resp = client.list_storage_lens_configurations(AccountId=ACCOUNT_ID)
    assert len(resp["StorageLensConfigurationList"]) == 1
    # Note the ID is NOT the config ID from the put request
    # but the ID from the config itself
    assert resp["StorageLensConfigurationList"][0]["Id"] == "id-test"
    assert "StorageLensArn" in resp["StorageLensConfigurationList"][0]
    assert resp["StorageLensConfigurationList"][0]["IsEnabled"] is True
