import boto3
import json
import pytest
import sure  # noqa # pylint: disable=unused-import

from boto3 import Session
from botocore.client import ClientError
from moto import settings, mock_s3control, mock_config

# All tests for s3-control cannot be run under the server without a modification of the
# hosts file on your system. This is due to the fact that the URL to the host is in the form of:
# ACCOUNT_ID.s3-control.amazonaws.com <-- That Account ID part is the problem. If you want to
# make use of the moto server, update your hosts file for `THE_ACCOUNT_ID_FOR_MOTO.localhost`
# and this will work fine.

if not settings.TEST_SERVER_MODE:

    @mock_s3control
    @mock_config
    def test_config_list_account_pab():
        from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

        client = boto3.client("s3control", region_name="us-west-2")
        config_client = boto3.client("config", region_name="us-west-2")

        # Create the aggregator:
        account_aggregation_source = {
            "AccountIds": [ACCOUNT_ID],
            "AllAwsRegions": True,
        }
        config_client.put_configuration_aggregator(
            ConfigurationAggregatorName="testing",
            AccountAggregationSources=[account_aggregation_source],
        )

        # Without a PAB in place:
        result = config_client.list_discovered_resources(
            resourceType="AWS::S3::AccountPublicAccessBlock"
        )
        assert not result["resourceIdentifiers"]
        result = config_client.list_aggregate_discovered_resources(
            ResourceType="AWS::S3::AccountPublicAccessBlock",
            ConfigurationAggregatorName="testing",
        )
        assert not result["ResourceIdentifiers"]

        # Create a PAB:
        client.put_public_access_block(
            AccountId=ACCOUNT_ID,
            PublicAccessBlockConfiguration={
                "BlockPublicAcls": True,
                "IgnorePublicAcls": True,
                "BlockPublicPolicy": True,
                "RestrictPublicBuckets": True,
            },
        )

        # Test that successful queries work (non-aggregated):
        result = config_client.list_discovered_resources(
            resourceType="AWS::S3::AccountPublicAccessBlock"
        )
        assert result["resourceIdentifiers"] == [
            {
                "resourceType": "AWS::S3::AccountPublicAccessBlock",
                "resourceId": ACCOUNT_ID,
            }
        ]
        result = config_client.list_discovered_resources(
            resourceType="AWS::S3::AccountPublicAccessBlock",
            resourceIds=[ACCOUNT_ID, "nope"],
        )
        assert result["resourceIdentifiers"] == [
            {
                "resourceType": "AWS::S3::AccountPublicAccessBlock",
                "resourceId": ACCOUNT_ID,
            }
        ]
        result = config_client.list_discovered_resources(
            resourceType="AWS::S3::AccountPublicAccessBlock", resourceName=""
        )
        assert result["resourceIdentifiers"] == [
            {
                "resourceType": "AWS::S3::AccountPublicAccessBlock",
                "resourceId": ACCOUNT_ID,
            }
        ]

        # Test that successful queries work (aggregated):
        result = config_client.list_aggregate_discovered_resources(
            ResourceType="AWS::S3::AccountPublicAccessBlock",
            ConfigurationAggregatorName="testing",
        )
        regions = {region for region in Session().get_available_regions("config")}
        for r in result["ResourceIdentifiers"]:
            regions.remove(r.pop("SourceRegion"))
            assert r == {
                "ResourceType": "AWS::S3::AccountPublicAccessBlock",
                "SourceAccountId": ACCOUNT_ID,
                "ResourceId": ACCOUNT_ID,
            }

        # Just check that the len is the same -- this should be reasonable
        regions = {region for region in Session().get_available_regions("config")}
        result = config_client.list_aggregate_discovered_resources(
            ResourceType="AWS::S3::AccountPublicAccessBlock",
            ConfigurationAggregatorName="testing",
            Filters={"ResourceName": ""},
        )
        assert len(regions) == len(result["ResourceIdentifiers"])
        result = config_client.list_aggregate_discovered_resources(
            ResourceType="AWS::S3::AccountPublicAccessBlock",
            ConfigurationAggregatorName="testing",
            Filters={"ResourceName": "", "ResourceId": ACCOUNT_ID},
        )
        assert len(regions) == len(result["ResourceIdentifiers"])
        result = config_client.list_aggregate_discovered_resources(
            ResourceType="AWS::S3::AccountPublicAccessBlock",
            ConfigurationAggregatorName="testing",
            Filters={
                "ResourceName": "",
                "ResourceId": ACCOUNT_ID,
                "Region": "us-west-2",
            },
        )
        assert (
            result["ResourceIdentifiers"][0]["SourceRegion"] == "us-west-2"
            and len(result["ResourceIdentifiers"]) == 1
        )

        # Test aggregator pagination:
        result = config_client.list_aggregate_discovered_resources(
            ResourceType="AWS::S3::AccountPublicAccessBlock",
            ConfigurationAggregatorName="testing",
            Limit=1,
        )
        regions = sorted(
            [region for region in Session().get_available_regions("config")]
        )
        assert result["ResourceIdentifiers"][0] == {
            "ResourceType": "AWS::S3::AccountPublicAccessBlock",
            "SourceAccountId": ACCOUNT_ID,
            "ResourceId": ACCOUNT_ID,
            "SourceRegion": regions[0],
        }
        assert result["NextToken"] == regions[1]

        # Get the next region:
        result = config_client.list_aggregate_discovered_resources(
            ResourceType="AWS::S3::AccountPublicAccessBlock",
            ConfigurationAggregatorName="testing",
            Limit=1,
            NextToken=regions[1],
        )
        assert result["ResourceIdentifiers"][0] == {
            "ResourceType": "AWS::S3::AccountPublicAccessBlock",
            "SourceAccountId": ACCOUNT_ID,
            "ResourceId": ACCOUNT_ID,
            "SourceRegion": regions[1],
        }

        # Non-aggregated with incorrect info:
        result = config_client.list_discovered_resources(
            resourceType="AWS::S3::AccountPublicAccessBlock", resourceName="nope"
        )
        assert not result["resourceIdentifiers"]
        result = config_client.list_discovered_resources(
            resourceType="AWS::S3::AccountPublicAccessBlock", resourceIds=["nope"]
        )
        assert not result["resourceIdentifiers"]

        # Aggregated with incorrect info:
        result = config_client.list_aggregate_discovered_resources(
            ResourceType="AWS::S3::AccountPublicAccessBlock",
            ConfigurationAggregatorName="testing",
            Filters={"ResourceName": "nope"},
        )
        assert not result["ResourceIdentifiers"]
        result = config_client.list_aggregate_discovered_resources(
            ResourceType="AWS::S3::AccountPublicAccessBlock",
            ConfigurationAggregatorName="testing",
            Filters={"ResourceId": "nope"},
        )
        assert not result["ResourceIdentifiers"]
        result = config_client.list_aggregate_discovered_resources(
            ResourceType="AWS::S3::AccountPublicAccessBlock",
            ConfigurationAggregatorName="testing",
            Filters={"Region": "Nope"},
        )
        assert not result["ResourceIdentifiers"]

    @mock_s3control
    @mock_config
    def test_config_get_account_pab():
        from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

        client = boto3.client("s3control", region_name="us-west-2")
        config_client = boto3.client("config", region_name="us-west-2")

        # Create the aggregator:
        account_aggregation_source = {
            "AccountIds": [ACCOUNT_ID],
            "AllAwsRegions": True,
        }
        config_client.put_configuration_aggregator(
            ConfigurationAggregatorName="testing",
            AccountAggregationSources=[account_aggregation_source],
        )

        # Without a PAB in place:
        with pytest.raises(ClientError) as ce:
            config_client.get_resource_config_history(
                resourceType="AWS::S3::AccountPublicAccessBlock", resourceId=ACCOUNT_ID
            )
        assert ce.value.response["Error"]["Code"] == "ResourceNotDiscoveredException"
        # aggregate
        result = config_client.batch_get_resource_config(
            resourceKeys=[
                {
                    "resourceType": "AWS::S3::AccountPublicAccessBlock",
                    "resourceId": "ACCOUNT_ID",
                }
            ]
        )
        assert not result["baseConfigurationItems"]
        result = config_client.batch_get_aggregate_resource_config(
            ConfigurationAggregatorName="testing",
            ResourceIdentifiers=[
                {
                    "SourceAccountId": ACCOUNT_ID,
                    "SourceRegion": "us-west-2",
                    "ResourceId": ACCOUNT_ID,
                    "ResourceType": "AWS::S3::AccountPublicAccessBlock",
                    "ResourceName": "",
                }
            ],
        )
        assert not result["BaseConfigurationItems"]

        # Create a PAB:
        client.put_public_access_block(
            AccountId=ACCOUNT_ID,
            PublicAccessBlockConfiguration={
                "BlockPublicAcls": True,
                "IgnorePublicAcls": True,
                "BlockPublicPolicy": True,
                "RestrictPublicBuckets": True,
            },
        )

        # Get the proper config:
        proper_config = {
            "blockPublicAcls": True,
            "ignorePublicAcls": True,
            "blockPublicPolicy": True,
            "restrictPublicBuckets": True,
        }
        result = config_client.get_resource_config_history(
            resourceType="AWS::S3::AccountPublicAccessBlock", resourceId=ACCOUNT_ID
        )
        assert (
            json.loads(result["configurationItems"][0]["configuration"])
            == proper_config
        )
        assert (
            result["configurationItems"][0]["accountId"]
            == result["configurationItems"][0]["resourceId"]
            == ACCOUNT_ID
        )
        result = config_client.batch_get_resource_config(
            resourceKeys=[
                {
                    "resourceType": "AWS::S3::AccountPublicAccessBlock",
                    "resourceId": ACCOUNT_ID,
                }
            ]
        )
        assert len(result["baseConfigurationItems"]) == 1
        assert (
            json.loads(result["baseConfigurationItems"][0]["configuration"])
            == proper_config
        )
        assert (
            result["baseConfigurationItems"][0]["accountId"]
            == result["baseConfigurationItems"][0]["resourceId"]
            == ACCOUNT_ID
        )

        for region in Session().get_available_regions("s3control"):
            result = config_client.batch_get_aggregate_resource_config(
                ConfigurationAggregatorName="testing",
                ResourceIdentifiers=[
                    {
                        "SourceAccountId": ACCOUNT_ID,
                        "SourceRegion": region,
                        "ResourceId": ACCOUNT_ID,
                        "ResourceType": "AWS::S3::AccountPublicAccessBlock",
                        "ResourceName": "",
                    }
                ],
            )
            assert len(result["BaseConfigurationItems"]) == 1
            assert (
                json.loads(result["BaseConfigurationItems"][0]["configuration"])
                == proper_config
            )
