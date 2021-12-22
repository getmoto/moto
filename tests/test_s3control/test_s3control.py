"""Unit tests for s3control-supported APIs."""
import logging

import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import
from botocore.exceptions import ClientError

from moto import mock_s3control, mock_organizations

logger = logging.getLogger(__name__)


# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


def standard_organization_with_account(account_name="mock-account"):
    client = boto3.client("organizations", region_name="eu-central-1")
    client.create_organization(FeatureSet="ALL")
    create_status = client.create_account(
        AccountName=account_name, Email="mock@email.com"
    )["CreateAccountStatus"]
    return create_status["AccountId"]


@mock_organizations
@mock_s3control
def test_get_public_access_block():
    account_id = standard_organization_with_account()
    client = boto3.client("s3control", region_name="eu-west-1")
    client.put_public_access_block(
        AccountId=account_id,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": False,
            "RestrictPublicBuckets": False,
        },
    )
    response = client.get_public_access_block(AccountId=account_id)
    response["PublicAccessBlockConfiguration"].should.have.key("BlockPublicAcls").equal(
        True
    )
    response["PublicAccessBlockConfiguration"].should.have.key(
        "IgnorePublicAcls"
    ).equal(True)
    response["PublicAccessBlockConfiguration"].should.have.key(
        "BlockPublicPolicy"
    ).equal(False)
    response["PublicAccessBlockConfiguration"].should.have.key(
        "RestrictPublicBuckets"
    ).equal(False)

    client.put_public_access_block(
        AccountId=account_id,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": True,
            "RestrictPublicBuckets": True,
        },
    )

    response = client.get_public_access_block(AccountId=account_id)
    response["PublicAccessBlockConfiguration"].should.have.key("BlockPublicAcls").equal(
        True
    )
    response["PublicAccessBlockConfiguration"].should.have.key(
        "IgnorePublicAcls"
    ).equal(True)
    response["PublicAccessBlockConfiguration"].should.have.key(
        "BlockPublicPolicy"
    ).equal(True)
    response["PublicAccessBlockConfiguration"].should.have.key(
        "RestrictPublicBuckets"
    ).equal(True)


@mock_organizations
@mock_s3control
def test_delete_public_access_block():
    account_id = standard_organization_with_account()
    client = boto3.client("s3control", region_name="eu-west-1")
    with pytest.raises(ClientError) as excinfo:
        client.get_public_access_block(AccountId=account_id)
    assert (
        "An error occurred (AccessDenied) when calling the GetPublicAccessBlock operation"
        in str(excinfo.value)
    )
    client.put_public_access_block(
        AccountId=account_id,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": True,
            "RestrictPublicBuckets": True,
        },
    )
    client.get_public_access_block(AccountId=account_id)
    client.delete_public_access_block(AccountId=account_id)

    with pytest.raises(ClientError) as excinfo:
        client.get_public_access_block(AccountId=account_id)
    assert "The public access block configuration was not found" in str(excinfo.value)
