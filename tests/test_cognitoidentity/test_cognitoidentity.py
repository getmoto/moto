from __future__ import unicode_literals

import boto3
from botocore.exceptions import ClientError
from nose.tools import assert_raises

from moto import mock_cognitoidentity
from moto.cognitoidentity.utils import get_random_identity_id
from moto.core import ACCOUNT_ID
from uuid import UUID


@mock_cognitoidentity
def test_create_identity_pool():
    conn = boto3.client("cognito-identity", "us-west-2")

    result = conn.create_identity_pool(
        IdentityPoolName="TestPool",
        AllowUnauthenticatedIdentities=False,
        SupportedLoginProviders={"graph.facebook.com": "123456789012345"},
        DeveloperProviderName="devname",
        OpenIdConnectProviderARNs=[
            "arn:aws:rds:eu-west-2:{}:db:mysql-db".format(ACCOUNT_ID)
        ],
        CognitoIdentityProviders=[
            {
                "ProviderName": "testprovider",
                "ClientId": "CLIENT12345",
                "ServerSideTokenCheck": True,
            }
        ],
        SamlProviderARNs=["arn:aws:rds:eu-west-2:{}:db:mysql-db".format(ACCOUNT_ID)],
    )
    assert result["IdentityPoolId"] != ""


@mock_cognitoidentity
def test_describe_identity_pool():
    conn = boto3.client("cognito-identity", "us-west-2")

    res = conn.create_identity_pool(
        IdentityPoolName="TestPool",
        AllowUnauthenticatedIdentities=False,
        SupportedLoginProviders={"graph.facebook.com": "123456789012345"},
        DeveloperProviderName="devname",
        OpenIdConnectProviderARNs=[
            "arn:aws:rds:eu-west-2:{}:db:mysql-db".format(ACCOUNT_ID)
        ],
        CognitoIdentityProviders=[
            {
                "ProviderName": "testprovider",
                "ClientId": "CLIENT12345",
                "ServerSideTokenCheck": True,
            }
        ],
        SamlProviderARNs=["arn:aws:rds:eu-west-2:{}:db:mysql-db".format(ACCOUNT_ID)],
    )

    result = conn.describe_identity_pool(IdentityPoolId=res["IdentityPoolId"])

    assert result["IdentityPoolId"] == res["IdentityPoolId"]
    assert (
        result["AllowUnauthenticatedIdentities"]
        == res["AllowUnauthenticatedIdentities"]
    )
    assert result["SupportedLoginProviders"] == res["SupportedLoginProviders"]
    assert result["DeveloperProviderName"] == res["DeveloperProviderName"]
    assert result["OpenIdConnectProviderARNs"] == res["OpenIdConnectProviderARNs"]
    assert result["CognitoIdentityProviders"] == res["CognitoIdentityProviders"]
    assert result["SamlProviderARNs"] == res["SamlProviderARNs"]


@mock_cognitoidentity
def test_describe_identity_pool_with_invalid_id_raises_error():
    conn = boto3.client("cognito-identity", "us-west-2")

    with assert_raises(ClientError) as cm:
        conn.describe_identity_pool(IdentityPoolId="us-west-2_non-existent")

        cm.exception.operation_name.should.equal("DescribeIdentityPool")
        cm.exception.response["Error"]["Code"].should.equal("ResourceNotFoundException")
        cm.exception.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)


# testing a helper function
def test_get_random_identity_id():
    identity_id = get_random_identity_id("us-west-2")
    region, id = identity_id.split(":")
    region.should.equal("us-west-2")
    UUID(id, version=4)  # Will throw an error if it's not a valid UUID


@mock_cognitoidentity
def test_get_id():
    # These two do NOT work in server mode. They just don't return the data from the model.
    conn = boto3.client("cognito-identity", "us-west-2")
    result = conn.get_id(
        AccountId="someaccount",
        IdentityPoolId="us-west-2:12345",
        Logins={"someurl": "12345"},
    )
    assert (
        result.get("IdentityId", "").startswith("us-west-2")
        or result.get("ResponseMetadata").get("HTTPStatusCode") == 200
    )


@mock_cognitoidentity
def test_get_credentials_for_identity():
    # These two do NOT work in server mode. They just don't return the data from the model.
    conn = boto3.client("cognito-identity", "us-west-2")
    result = conn.get_credentials_for_identity(IdentityId="12345")

    assert (
        result.get("Expiration", 0) > 0
        or result.get("ResponseMetadata").get("HTTPStatusCode") == 200
    )
    assert (
        result.get("IdentityId") == "12345"
        or result.get("ResponseMetadata").get("HTTPStatusCode") == 200
    )


@mock_cognitoidentity
def test_get_open_id_token_for_developer_identity():
    conn = boto3.client("cognito-identity", "us-west-2")
    result = conn.get_open_id_token_for_developer_identity(
        IdentityPoolId="us-west-2:12345",
        IdentityId="12345",
        Logins={"someurl": "12345"},
        TokenDuration=123,
    )
    assert len(result["Token"]) > 0
    assert result["IdentityId"] == "12345"


@mock_cognitoidentity
def test_get_open_id_token_for_developer_identity_when_no_explicit_identity_id():
    conn = boto3.client("cognito-identity", "us-west-2")
    result = conn.get_open_id_token_for_developer_identity(
        IdentityPoolId="us-west-2:12345", Logins={"someurl": "12345"}, TokenDuration=123
    )
    assert len(result["Token"]) > 0
    assert len(result["IdentityId"]) > 0


@mock_cognitoidentity
def test_get_open_id_token():
    conn = boto3.client("cognito-identity", "us-west-2")
    result = conn.get_open_id_token(IdentityId="12345", Logins={"someurl": "12345"})
    assert len(result["Token"]) > 0
    assert result["IdentityId"] == "12345"
