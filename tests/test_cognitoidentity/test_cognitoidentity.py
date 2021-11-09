import boto3
import sure  # noqa # pylint: disable=unused-import
from botocore.exceptions import ClientError
import pytest

from moto import mock_cognitoidentity
from moto.cognitoidentity.utils import get_random_identity_id
from moto.core import ACCOUNT_ID
from uuid import UUID


@mock_cognitoidentity
@pytest.mark.parametrize("name", ["pool#name", "with!excl", "with?quest"])
def test_create_identity_pool_invalid_name(name):
    conn = boto3.client("cognito-identity", "us-west-2")

    with pytest.raises(ClientError) as exc:
        conn.create_identity_pool(
            IdentityPoolName=name, AllowUnauthenticatedIdentities=False
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.equal(
        f"1 validation error detected: Value '{name}' at 'identityPoolName' failed to satisfy constraint: Member must satisfy regular expression pattern: [\\w\\s+=,.@-]+"
    )


@mock_cognitoidentity
@pytest.mark.parametrize("name", ["x", "pool-", "pool_name", "with space"])
def test_create_identity_pool_valid_name(name):
    conn = boto3.client("cognito-identity", "us-west-2")

    conn.create_identity_pool(
        IdentityPoolName=name, AllowUnauthenticatedIdentities=False
    )


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


@pytest.mark.parametrize(
    "key,initial_value,updated_value",
    [
        (
            "SupportedLoginProviders",
            {"graph.facebook.com": "123456789012345"},
            {"graph.facebook.com": "123456789012345", "graph.google.com": "00000000"},
        ),
        ("SupportedLoginProviders", {"graph.facebook.com": "123456789012345"}, {}),
        ("DeveloperProviderName", "dev1", "dev2"),
    ],
)
@mock_cognitoidentity
def test_update_identity_pool(key, initial_value, updated_value):
    conn = boto3.client("cognito-identity", "us-west-2")

    res = conn.create_identity_pool(
        IdentityPoolName="TestPool",
        AllowUnauthenticatedIdentities=False,
        **dict({key: initial_value}),
    )

    first = conn.describe_identity_pool(IdentityPoolId=res["IdentityPoolId"])
    first[key].should.equal(initial_value)

    response = conn.update_identity_pool(
        IdentityPoolId=res["IdentityPoolId"],
        IdentityPoolName="TestPool",
        AllowUnauthenticatedIdentities=False,
        **dict({key: updated_value}),
    )
    response[key].should.equal(updated_value)

    second = conn.describe_identity_pool(IdentityPoolId=res["IdentityPoolId"])
    second[key].should.equal(response[key])


@mock_cognitoidentity
def test_describe_identity_pool_with_invalid_id_raises_error():
    conn = boto3.client("cognito-identity", "us-west-2")
    with pytest.raises(ClientError) as cm:
        conn.describe_identity_pool(IdentityPoolId="us-west-2_non-existent")

    cm.value.operation_name.should.equal("DescribeIdentityPool")
    cm.value.response["Error"]["Code"].should.equal("ResourceNotFoundException")
    cm.value.response["Error"]["Message"].should.equal("us-west-2_non-existent")
    cm.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)


# testing a helper function
def test_get_random_identity_id():
    identity_id = get_random_identity_id("us-west-2")
    region, identity_id = identity_id.split(":")
    region.should.equal("us-west-2")
    UUID(identity_id, version=4)  # Will throw an error if it's not a valid UUID


@mock_cognitoidentity
def test_get_id():
    # These two do NOT work in server mode. They just don't return the data from the model.
    conn = boto3.client("cognito-identity", "us-west-2")
    identity_pool_data = conn.create_identity_pool(
        IdentityPoolName="test_identity_pool", AllowUnauthenticatedIdentities=True
    )
    result = conn.get_id(
        AccountId="someaccount",
        IdentityPoolId=identity_pool_data["IdentityPoolId"],
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


@mock_cognitoidentity
def test_list_identities():
    conn = boto3.client("cognito-identity", "us-west-2")
    identity_pool_data = conn.create_identity_pool(
        IdentityPoolName="test_identity_pool", AllowUnauthenticatedIdentities=True
    )
    identity_pool_id = identity_pool_data["IdentityPoolId"]
    identity_data = conn.get_id(
        AccountId="someaccount",
        IdentityPoolId=identity_pool_id,
        Logins={"someurl": "12345"},
    )
    identity_id = identity_data["IdentityId"]
    identities = conn.list_identities(IdentityPoolId=identity_pool_id, MaxResults=123)
    assert "IdentityPoolId" in identities and "Identities" in identities
    assert identity_id in [x["IdentityId"] for x in identities["Identities"]]
