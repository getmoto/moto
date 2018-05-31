from __future__ import unicode_literals

import boto3
import json
import os
import uuid

from jose import jws
from moto import mock_cognitoidp
import sure  # noqa


@mock_cognitoidp
def test_create_user_pool():
    conn = boto3.client("cognito-idp", "us-west-2")

    name = str(uuid.uuid4())
    value = str(uuid.uuid4())
    result = conn.create_user_pool(
        PoolName=name,
        LambdaConfig={
            "PreSignUp": value
        }
    )

    result["UserPool"]["Id"].should_not.be.none
    result["UserPool"]["Name"].should.equal(name)
    result["UserPool"]["LambdaConfig"]["PreSignUp"].should.equal(value)


@mock_cognitoidp
def test_list_user_pools():
    conn = boto3.client("cognito-idp", "us-west-2")

    name = str(uuid.uuid4())
    conn.create_user_pool(PoolName=name)
    result = conn.list_user_pools(MaxResults=10)
    result["UserPools"].should.have.length_of(1)
    result["UserPools"][0]["Name"].should.equal(name)


@mock_cognitoidp
def test_describe_user_pool():
    conn = boto3.client("cognito-idp", "us-west-2")

    name = str(uuid.uuid4())
    value = str(uuid.uuid4())
    user_pool_details = conn.create_user_pool(
        PoolName=name,
        LambdaConfig={
            "PreSignUp": value
        }
    )

    result = conn.describe_user_pool(UserPoolId=user_pool_details["UserPool"]["Id"])
    result["UserPool"]["Name"].should.equal(name)
    result["UserPool"]["LambdaConfig"]["PreSignUp"].should.equal(value)


@mock_cognitoidp
def test_delete_user_pool():
    conn = boto3.client("cognito-idp", "us-west-2")

    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    conn.list_user_pools(MaxResults=10)["UserPools"].should.have.length_of(1)
    conn.delete_user_pool(UserPoolId=user_pool_id)
    conn.list_user_pools(MaxResults=10)["UserPools"].should.have.length_of(0)


@mock_cognitoidp
def test_create_user_pool_domain():
    conn = boto3.client("cognito-idp", "us-west-2")

    domain = str(uuid.uuid4())
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    result = conn.create_user_pool_domain(UserPoolId=user_pool_id, Domain=domain)
    result["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)


@mock_cognitoidp
def test_describe_user_pool_domain():
    conn = boto3.client("cognito-idp", "us-west-2")

    domain = str(uuid.uuid4())
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    conn.create_user_pool_domain(UserPoolId=user_pool_id, Domain=domain)
    result = conn.describe_user_pool_domain(Domain=domain)
    result["DomainDescription"]["Domain"].should.equal(domain)
    result["DomainDescription"]["UserPoolId"].should.equal(user_pool_id)
    result["DomainDescription"]["AWSAccountId"].should_not.be.none


@mock_cognitoidp
def test_delete_user_pool_domain():
    conn = boto3.client("cognito-idp", "us-west-2")

    domain = str(uuid.uuid4())
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    conn.create_user_pool_domain(UserPoolId=user_pool_id, Domain=domain)
    result = conn.delete_user_pool_domain(UserPoolId=user_pool_id, Domain=domain)
    result["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    result = conn.describe_user_pool_domain(Domain=domain)
    # This is a surprising behavior of the real service: describing a missing domain comes
    # back with status 200 and a DomainDescription of {}
    result["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    result["DomainDescription"].keys().should.have.length_of(0)


@mock_cognitoidp
def test_create_user_pool_client():
    conn = boto3.client("cognito-idp", "us-west-2")

    client_name = str(uuid.uuid4())
    value = str(uuid.uuid4())
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    result = conn.create_user_pool_client(
        UserPoolId=user_pool_id,
        ClientName=client_name,
        CallbackURLs=[value],
    )

    result["UserPoolClient"]["UserPoolId"].should.equal(user_pool_id)
    result["UserPoolClient"]["ClientId"].should_not.be.none
    result["UserPoolClient"]["ClientName"].should.equal(client_name)
    result["UserPoolClient"]["CallbackURLs"].should.have.length_of(1)
    result["UserPoolClient"]["CallbackURLs"][0].should.equal(value)


@mock_cognitoidp
def test_list_user_pool_clients():
    conn = boto3.client("cognito-idp", "us-west-2")

    client_name = str(uuid.uuid4())
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    conn.create_user_pool_client(UserPoolId=user_pool_id, ClientName=client_name)
    result = conn.list_user_pool_clients(UserPoolId=user_pool_id, MaxResults=10)
    result["UserPoolClients"].should.have.length_of(1)
    result["UserPoolClients"][0]["ClientName"].should.equal(client_name)


@mock_cognitoidp
def test_describe_user_pool_client():
    conn = boto3.client("cognito-idp", "us-west-2")

    client_name = str(uuid.uuid4())
    value = str(uuid.uuid4())
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    client_details = conn.create_user_pool_client(
        UserPoolId=user_pool_id,
        ClientName=client_name,
        CallbackURLs=[value],
    )

    result = conn.describe_user_pool_client(
        UserPoolId=user_pool_id,
        ClientId=client_details["UserPoolClient"]["ClientId"],
    )

    result["UserPoolClient"]["ClientName"].should.equal(client_name)
    result["UserPoolClient"]["CallbackURLs"].should.have.length_of(1)
    result["UserPoolClient"]["CallbackURLs"][0].should.equal(value)


@mock_cognitoidp
def test_update_user_pool_client():
    conn = boto3.client("cognito-idp", "us-west-2")

    old_client_name = str(uuid.uuid4())
    new_client_name = str(uuid.uuid4())
    old_value = str(uuid.uuid4())
    new_value = str(uuid.uuid4())
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    client_details = conn.create_user_pool_client(
        UserPoolId=user_pool_id,
        ClientName=old_client_name,
        CallbackURLs=[old_value],
    )

    result = conn.update_user_pool_client(
        UserPoolId=user_pool_id,
        ClientId=client_details["UserPoolClient"]["ClientId"],
        ClientName=new_client_name,
        CallbackURLs=[new_value],
    )

    result["UserPoolClient"]["ClientName"].should.equal(new_client_name)
    result["UserPoolClient"]["CallbackURLs"].should.have.length_of(1)
    result["UserPoolClient"]["CallbackURLs"][0].should.equal(new_value)


@mock_cognitoidp
def test_delete_user_pool_client():
    conn = boto3.client("cognito-idp", "us-west-2")

    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    client_details = conn.create_user_pool_client(
        UserPoolId=user_pool_id,
        ClientName=str(uuid.uuid4()),
    )

    conn.delete_user_pool_client(
        UserPoolId=user_pool_id,
        ClientId=client_details["UserPoolClient"]["ClientId"],
    )

    caught = False
    try:
        conn.describe_user_pool_client(
            UserPoolId=user_pool_id,
            ClientId=client_details["UserPoolClient"]["ClientId"],
        )
    except conn.exceptions.ResourceNotFoundException:
        caught = True

    caught.should.be.true


@mock_cognitoidp
def test_create_identity_provider():
    conn = boto3.client("cognito-idp", "us-west-2")

    provider_name = str(uuid.uuid4())
    provider_type = "Facebook"
    value = str(uuid.uuid4())
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    result = conn.create_identity_provider(
        UserPoolId=user_pool_id,
        ProviderName=provider_name,
        ProviderType=provider_type,
        ProviderDetails={
            "thing": value
        },
    )

    result["IdentityProvider"]["UserPoolId"].should.equal(user_pool_id)
    result["IdentityProvider"]["ProviderName"].should.equal(provider_name)
    result["IdentityProvider"]["ProviderType"].should.equal(provider_type)
    result["IdentityProvider"]["ProviderDetails"]["thing"].should.equal(value)


@mock_cognitoidp
def test_list_identity_providers():
    conn = boto3.client("cognito-idp", "us-west-2")

    provider_name = str(uuid.uuid4())
    provider_type = "Facebook"
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    conn.create_identity_provider(
        UserPoolId=user_pool_id,
        ProviderName=provider_name,
        ProviderType=provider_type,
        ProviderDetails={},
    )

    result = conn.list_identity_providers(
        UserPoolId=user_pool_id,
        MaxResults=10,
    )

    result["Providers"].should.have.length_of(1)
    result["Providers"][0]["ProviderName"].should.equal(provider_name)
    result["Providers"][0]["ProviderType"].should.equal(provider_type)


@mock_cognitoidp
def test_describe_identity_providers():
    conn = boto3.client("cognito-idp", "us-west-2")

    provider_name = str(uuid.uuid4())
    provider_type = "Facebook"
    value = str(uuid.uuid4())
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    conn.create_identity_provider(
        UserPoolId=user_pool_id,
        ProviderName=provider_name,
        ProviderType=provider_type,
        ProviderDetails={
            "thing": value
        },
    )

    result = conn.describe_identity_provider(
        UserPoolId=user_pool_id,
        ProviderName=provider_name,
    )

    result["IdentityProvider"]["UserPoolId"].should.equal(user_pool_id)
    result["IdentityProvider"]["ProviderName"].should.equal(provider_name)
    result["IdentityProvider"]["ProviderType"].should.equal(provider_type)
    result["IdentityProvider"]["ProviderDetails"]["thing"].should.equal(value)


@mock_cognitoidp
def test_delete_identity_providers():
    conn = boto3.client("cognito-idp", "us-west-2")

    provider_name = str(uuid.uuid4())
    provider_type = "Facebook"
    value = str(uuid.uuid4())
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    conn.create_identity_provider(
        UserPoolId=user_pool_id,
        ProviderName=provider_name,
        ProviderType=provider_type,
        ProviderDetails={
            "thing": value
        },
    )

    conn.delete_identity_provider(UserPoolId=user_pool_id, ProviderName=provider_name)

    caught = False
    try:
        conn.describe_identity_provider(
            UserPoolId=user_pool_id,
            ProviderName=provider_name,
        )
    except conn.exceptions.ResourceNotFoundException:
        caught = True

    caught.should.be.true


@mock_cognitoidp
def test_admin_create_user():
    conn = boto3.client("cognito-idp", "us-west-2")

    username = str(uuid.uuid4())
    value = str(uuid.uuid4())
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    result = conn.admin_create_user(
        UserPoolId=user_pool_id,
        Username=username,
        UserAttributes=[
            {"Name": "thing", "Value": value}
        ],
    )

    result["User"]["Username"].should.equal(username)
    result["User"]["UserStatus"].should.equal("FORCE_CHANGE_PASSWORD")
    result["User"]["Attributes"].should.have.length_of(1)
    result["User"]["Attributes"][0]["Name"].should.equal("thing")
    result["User"]["Attributes"][0]["Value"].should.equal(value)


@mock_cognitoidp
def test_admin_get_user():
    conn = boto3.client("cognito-idp", "us-west-2")

    username = str(uuid.uuid4())
    value = str(uuid.uuid4())
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    conn.admin_create_user(
        UserPoolId=user_pool_id,
        Username=username,
        UserAttributes=[
            {"Name": "thing", "Value": value}
        ],
    )

    result = conn.admin_get_user(UserPoolId=user_pool_id, Username=username)
    result["Username"].should.equal(username)
    result["UserAttributes"].should.have.length_of(1)
    result["UserAttributes"][0]["Name"].should.equal("thing")
    result["UserAttributes"][0]["Value"].should.equal(value)


@mock_cognitoidp
def test_list_users():
    conn = boto3.client("cognito-idp", "us-west-2")

    username = str(uuid.uuid4())
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    conn.admin_create_user(UserPoolId=user_pool_id, Username=username)
    result = conn.list_users(UserPoolId=user_pool_id)
    result["Users"].should.have.length_of(1)
    result["Users"][0]["Username"].should.equal(username)


@mock_cognitoidp
def test_admin_delete_user():
    conn = boto3.client("cognito-idp", "us-west-2")

    username = str(uuid.uuid4())
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    conn.admin_create_user(UserPoolId=user_pool_id, Username=username)
    conn.admin_delete_user(UserPoolId=user_pool_id, Username=username)

    caught = False
    try:
        conn.admin_get_user(UserPoolId=user_pool_id, Username=username)
    except conn.exceptions.ResourceNotFoundException:
        caught = True

    caught.should.be.true


def authentication_flow(conn):
    username = str(uuid.uuid4())
    temporary_password = str(uuid.uuid4())
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    client_id = conn.create_user_pool_client(
        UserPoolId=user_pool_id,
        ClientName=str(uuid.uuid4()),
    )["UserPoolClient"]["ClientId"]

    conn.admin_create_user(
        UserPoolId=user_pool_id,
        Username=username,
        TemporaryPassword=temporary_password,
    )

    result = conn.admin_initiate_auth(
        UserPoolId=user_pool_id,
        ClientId=client_id,
        AuthFlow="ADMIN_NO_SRP_AUTH",
        AuthParameters={
            "USERNAME": username,
            "PASSWORD": temporary_password
        },
    )

    # A newly created user is forced to set a new password
    result["ChallengeName"].should.equal("NEW_PASSWORD_REQUIRED")
    result["Session"].should_not.be.none

    # This sets a new password and logs the user in (creates tokens)
    new_password = str(uuid.uuid4())
    result = conn.respond_to_auth_challenge(
        Session=result["Session"],
        ClientId=client_id,
        ChallengeName="NEW_PASSWORD_REQUIRED",
        ChallengeResponses={
            "USERNAME": username,
            "NEW_PASSWORD": new_password
        }
    )

    result["AuthenticationResult"]["IdToken"].should_not.be.none
    result["AuthenticationResult"]["AccessToken"].should_not.be.none

    return {
        "user_pool_id": user_pool_id,
        "client_id": client_id,
        "id_token": result["AuthenticationResult"]["IdToken"],
        "access_token": result["AuthenticationResult"]["AccessToken"],
        "username": username,
        "password": new_password,
    }


@mock_cognitoidp
def test_authentication_flow():
    conn = boto3.client("cognito-idp", "us-west-2")

    authentication_flow(conn)


@mock_cognitoidp
def test_token_legitimacy():
    conn = boto3.client("cognito-idp", "us-west-2")

    path = "../../moto/cognitoidp/resources/jwks-public.json"
    with open(os.path.join(os.path.dirname(__file__), path)) as f:
        json_web_key = json.loads(f.read())["keys"][0]

    outputs = authentication_flow(conn)
    id_token = outputs["id_token"]
    access_token = outputs["access_token"]
    client_id = outputs["client_id"]
    issuer = "https://cognito-idp.us-west-2.amazonaws.com/{}".format(outputs["user_pool_id"])
    id_claims = json.loads(jws.verify(id_token, json_web_key, "RS256"))
    id_claims["iss"].should.equal(issuer)
    id_claims["aud"].should.equal(client_id)
    access_claims = json.loads(jws.verify(access_token, json_web_key, "RS256"))
    access_claims["iss"].should.equal(issuer)
    access_claims["aud"].should.equal(client_id)


@mock_cognitoidp
def test_change_password():
    conn = boto3.client("cognito-idp", "us-west-2")

    outputs = authentication_flow(conn)

    # Take this opportunity to test change_password, which requires an access token.
    newer_password = str(uuid.uuid4())
    conn.change_password(
        AccessToken=outputs["access_token"],
        PreviousPassword=outputs["password"],
        ProposedPassword=newer_password,
    )

    # Log in again, which should succeed without a challenge because the user is no
    # longer in the force-new-password state.
    result = conn.admin_initiate_auth(
        UserPoolId=outputs["user_pool_id"],
        ClientId=outputs["client_id"],
        AuthFlow="ADMIN_NO_SRP_AUTH",
        AuthParameters={
            "USERNAME": outputs["username"],
            "PASSWORD": newer_password,
        },
    )

    result["AuthenticationResult"].should_not.be.none


@mock_cognitoidp
def test_forgot_password():
    conn = boto3.client("cognito-idp", "us-west-2")

    result = conn.forgot_password(ClientId=str(uuid.uuid4()), Username=str(uuid.uuid4()))
    result["CodeDeliveryDetails"].should_not.be.none


@mock_cognitoidp
def test_confirm_forgot_password():
    conn = boto3.client("cognito-idp", "us-west-2")

    username = str(uuid.uuid4())
    user_pool_id = conn.create_user_pool(PoolName=str(uuid.uuid4()))["UserPool"]["Id"]
    client_id = conn.create_user_pool_client(
        UserPoolId=user_pool_id,
        ClientName=str(uuid.uuid4()),
    )["UserPoolClient"]["ClientId"]

    conn.admin_create_user(
        UserPoolId=user_pool_id,
        Username=username,
        TemporaryPassword=str(uuid.uuid4()),
    )

    conn.confirm_forgot_password(
        ClientId=client_id,
        Username=username,
        ConfirmationCode=str(uuid.uuid4()),
        Password=str(uuid.uuid4()),
    )
