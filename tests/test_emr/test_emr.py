"""Unit tests for emr-supported APIs."""

import boto3
import pytest

from moto import mock_aws

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html

@pytest.fixture(name="client")
def fixture_emr_client():
    with mock_aws():
        yield boto3.client("emr", region_name="us-east-2")

@mock_aws
def test_put_and_get_block_public_access_configuration(client):
    client.put_block_public_access_configuration(
        BlockPublicAccessConfiguration={
            'BlockPublicSecurityGroupRules': True,
            'PermittedPublicSecurityGroupRuleRanges': [
                {
                    'MinRange': 10,
                    'MaxRange': 100
                },
            ]
        }
    )

    connection = client.get_block_public_access_configuration()
    assert connection["BlockPublicAccessConfiguration"]["BlockPublicSecurityGroupRules"]
    assert connection["BlockPublicAccessConfiguration"]["PermittedPublicSecurityGroupRuleRanges"][0]["MinRange"] == 10
    assert connection["BlockPublicAccessConfiguration"]["PermittedPublicSecurityGroupRuleRanges"][0]["MinRange"] == 100
    assert isinstance(connection["BlockPublicAccessConfigurationMetadata"]["CreatedByArn"], str)
    assert isinstance(connection["BlockPublicAccessConfigurationMetadata"]["CreationDateTime"], int)
     