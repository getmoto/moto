import json
from collections.abc import Iterable

import pytest
import requests

import moto.server as server
from moto.server import ThreadedMotoServer


def test_sign_up_user_without_authentication():
    backend = server.create_backend_app("cognito-idp")
    test_client = backend.test_client()

    # Create User Pool
    res = test_client.post(
        "/",
        data='{"PoolName": "test-pool"}',
        headers={
            "X-Amz-Target": "AWSCognitoIdentityProviderService.CreateUserPool",
            "Authorization": "AWS4-HMAC-SHA256 Credential=abcd/20010101/us-east-2/s3/aws4_request, SignedHeaders=host;x-amz-content-sha256;x-amz-date, Signature=...",
        },
    )
    user_pool_id = json.loads(res.data)["UserPool"]["Id"]

    # Create User Pool Client
    data = {
        "UserPoolId": user_pool_id,
        "ClientName": "some-client",
        "GenerateSecret": False,
        "ExplicitAuthFlows": ["ALLOW_USER_PASSWORD_AUTH"],
    }
    res = test_client.post(
        "/",
        data=json.dumps(data),
        headers={
            "X-Amz-Target": "AWSCognitoIdentityProviderService.CreateUserPoolClient",
            "Authorization": "AWS4-HMAC-SHA256 Credential=abcd/20010101/us-east-2/s3/aws4_request, SignedHeaders=host;x-amz-content-sha256;x-amz-date, Signature=...",
        },
    )
    client_id = json.loads(res.data)["UserPoolClient"]["ClientId"]

    # List User Pool Clients, to verify it exists
    data = {"UserPoolId": user_pool_id}
    res = test_client.post(
        "/",
        data=json.dumps(data),
        headers={
            "X-Amz-Target": "AWSCognitoIdentityProviderService.ListUserPoolClients",
            "Authorization": "AWS4-HMAC-SHA256 Credential=abcd/20010101/us-east-2/s3/aws4_request, SignedHeaders=host;x-amz-content-sha256;x-amz-date, Signature=...",
        },
    )
    assert len(json.loads(res.data)["UserPoolClients"]) == 1

    # Sign Up User
    data = {"ClientId": client_id, "Username": "test@gmail.com", "Password": "P2$Sword"}
    res = test_client.post(
        "/",
        data=json.dumps(data),
        headers={"X-Amz-Target": "AWSCognitoIdentityProviderService.SignUp"},
    )
    assert res.status_code == 200
    assert json.loads(res.data)["UserConfirmed"] is False

    # Confirm Sign Up User
    data = {
        "ClientId": client_id,
        "Username": "test@gmail.com",
        "ConfirmationCode": "sth",
    }
    res = test_client.post(
        "/",
        data=json.dumps(data),
        headers={"X-Amz-Target": "AWSCognitoIdentityProviderService.ConfirmSignUp"},
    )

    # Initiate Auth
    data = {
        "ClientId": client_id,
        "AuthFlow": "USER_PASSWORD_AUTH",
        "AuthParameters": {"USERNAME": "test@gmail.com", "PASSWORD": "P2$Sword"},
    }
    res = test_client.post(
        "/",
        data=json.dumps(data),
        headers={"X-Amz-Target": "AWSCognitoIdentityProviderService.InitiateAuth"},
    )
    assert res.status_code == 200
    access_token = json.loads(res.data)["AuthenticationResult"]["AccessToken"]

    # Get User
    data = {"AccessToken": access_token}
    res = test_client.post(
        "/",
        data=json.dumps(data),
        headers={"X-Amz-Target": "AWSCognitoIdentityProviderService.GetUser"},
    )
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["Username"] == "test@gmail.com"


def test_admin_create_user_without_authentication():
    backend = server.create_backend_app("cognito-idp")
    test_client = backend.test_client()

    # Create User Pool
    res = test_client.post(
        "/",
        data='{"PoolName": "test-pool"}',
        headers={
            "X-Amz-Target": "AWSCognitoIdentityProviderService.CreateUserPool",
            "Authorization": "AWS4-HMAC-SHA256 Credential=abcd/20010101/us-east-2/s3/aws4_request, SignedHeaders=host;x-amz-content-sha256;x-amz-date, Signature=...",
        },
    )
    user_pool_id = json.loads(res.data)["UserPool"]["Id"]

    # Create User Pool Client
    data = {
        "UserPoolId": user_pool_id,
        "ClientName": "some-client",
        "GenerateSecret": False,
        "ExplicitAuthFlows": ["ALLOW_USER_PASSWORD_AUTH"],
    }
    res = test_client.post(
        "/",
        data=json.dumps(data),
        headers={
            "X-Amz-Target": "AWSCognitoIdentityProviderService.CreateUserPoolClient",
            "Authorization": "AWS4-HMAC-SHA256 Credential=abcd/20010101/us-east-2/s3/aws4_request, SignedHeaders=host;x-amz-content-sha256;x-amz-date, Signature=...",
        },
    )
    client_id = json.loads(res.data)["UserPoolClient"]["ClientId"]

    # Admin Create User
    data = {
        "UserPoolId": user_pool_id,
        "Username": "test@gmail.com",
        "TemporaryPassword": "A!1a12345678",
    }
    res = test_client.post(
        "/",
        data=json.dumps(data),
        headers={
            "X-Amz-Target": "AWSCognitoIdentityProviderService.AdminCreateUser",
            "Authorization": "AWS4-HMAC-SHA256 Credential=abcd/20010101/us-east-2/s3/aws4_request, SignedHeaders=host;x-amz-content-sha256;x-amz-date, Signature=...",
        },
    )
    assert res.status_code == 200

    # Initiate Auth
    data = {
        "ClientId": client_id,
        "AuthFlow": "USER_PASSWORD_AUTH",
        "AuthParameters": {"USERNAME": "test@gmail.com", "PASSWORD": "A!1a12345678"},
    }
    res = test_client.post(
        "/",
        data=json.dumps(data),
        headers={"X-Amz-Target": "AWSCognitoIdentityProviderService.InitiateAuth"},
    )
    session = json.loads(res.data)["Session"]

    # Respond to Auth Challenge
    data = {
        "ClientId": client_id,
        "ChallengeName": "NEW_PASSWORD_REQUIRED",
        "ChallengeResponses": {
            "USERNAME": "test@gmail.com",
            "NEW_PASSWORD": "A!1aabcdefgh",
        },
        "Session": session,
    }
    res = test_client.post(
        "/",
        data=json.dumps(data),
        headers={
            "X-Amz-Target": "AWSCognitoIdentityProviderService.RespondToAuthChallenge"
        },
    )
    assert res.status_code == 200
    response = json.loads(res.data)

    assert "AuthenticationResult" in response
    assert "IdToken" in response["AuthenticationResult"]
    assert "AccessToken" in response["AuthenticationResult"]


def test_associate_software_token():
    backend = server.create_backend_app("cognito-idp")
    test_client = backend.test_client()

    # Create User Pool
    res = test_client.post(
        "/",
        data='{"PoolName": "test-pool"}',
        headers={
            "X-Amz-Target": "AWSCognitoIdentityProviderService.CreateUserPool",
            "Authorization": "AWS4-HMAC-SHA256 Credential=abcd/20010101/us-east-2/s3/aws4_request, SignedHeaders=host;x-amz-content-sha256;x-amz-date, Signature=...",
        },
    )
    user_pool_id = json.loads(res.data)["UserPool"]["Id"]

    # Create User Pool Client
    data = {
        "UserPoolId": user_pool_id,
        "ClientName": "some-client",
        "GenerateSecret": False,
        "ExplicitAuthFlows": ["ALLOW_USER_PASSWORD_AUTH"],
    }
    res = test_client.post(
        "/",
        data=json.dumps(data),
        headers={
            "X-Amz-Target": "AWSCognitoIdentityProviderService.CreateUserPoolClient",
            "Authorization": "AWS4-HMAC-SHA256 Credential=abcd/20010101/us-east-2/s3/aws4_request, SignedHeaders=host;x-amz-content-sha256;x-amz-date, Signature=...",
        },
    )
    client_id = json.loads(res.data)["UserPoolClient"]["ClientId"]

    # Sign Up User
    data = {
        "ClientId": client_id,
        "Username": "user_2_mfa",
        "Password": "12312sdfasASDFDSF$",
    }
    res = test_client.post(
        "/",
        data=json.dumps(data),
        headers={"X-Amz-Target": "AWSCognitoIdentityProviderService.SignUp"},
    )
    assert res.status_code == 200
    assert json.loads(res.data)["UserConfirmed"] is False

    # Confirm Sign Up User
    data = {"ClientId": client_id, "Username": "user_2_mfa", "ConfirmationCode": "sth"}
    res = test_client.post(
        "/",
        data=json.dumps(data),
        headers={"X-Amz-Target": "AWSCognitoIdentityProviderService.ConfirmSignUp"},
    )

    # Initiate Auth
    data = {
        "AuthFlow": "USER_PASSWORD_AUTH",
        "AuthParameters": {
            "USERNAME": "user_2_mfa",
            "PASSWORD": "12312sdfasASDFDSF$",
            "SECRET_HASH": "kIWuIv6ElVe9ahZHJ+gqvZe6CgEkVE/BjQmJcMSgF3E=",
        },
        "ClientId": client_id,
    }
    res = test_client.post(
        "/",
        data=json.dumps(data),
        headers={"X-Amz-Target": "AWSCognitoIdentityProviderService.InitiateAuth"},
    )
    auth_data = json.loads(res.data.decode("utf-8"))["AuthenticationResult"]

    # Get User
    data = {"AccessToken": auth_data["AccessToken"]}
    res = test_client.post(
        "/",
        data=json.dumps(data),
        headers={"X-Amz-Target": "AWSCognitoIdentityProviderService.GetUser"},
    )

    # Associate Software Token
    data = {"AccessToken": auth_data["AccessToken"]}
    res = test_client.post(
        "/",
        data=json.dumps(data),
        headers={
            "X-Amz-Target": "AWSCognitoIdentityProviderService.AssociateSoftwareToken"
        },
    )
    assert json.loads(res.data.decode("utf-8")) == {"SecretCode": "asdfasdfasdf"}


def test_jwks_endpoint_without_auth_header():
    """Test that the JWKS endpoint works directly on the cognitoidp backend."""
    backend = server.create_backend_app("cognito-idp")
    test_client = backend.test_client()

    res = test_client.get("/us-east-1_abc123/.well-known/jwks.json")
    assert res.status_code == 200
    data = json.loads(res.data)
    assert "keys" in data


@pytest.fixture(scope="module")
def moto_server_url() -> Iterable[str]:
    srv = ThreadedMotoServer(port=0)
    srv.start()
    host, port = srv.get_host_and_port()
    yield f"http://{host}:{port}"
    srv.stop()


def test_jwks_endpoint_on_moto_server(moto_server_url: str):
    """Regression test for https://github.com/getmoto/moto/issues/9570.

    In server mode, a plain GET to /{pool_id}/.well-known/jwks.json
    should return the JWKS public keys without requiring an Authorization
    header.
    """
    url = f"{moto_server_url}/us-east-1_abc123/.well-known/jwks.json"
    response = requests.get(url)
    assert response.status_code == 200
    data = response.json()
    assert "keys" in data
    assert len(data["keys"]) >= 1


def test_jwks_endpoint_non_us_east_1_region(moto_server_url: str):
    """JWKS endpoint should route correctly for pools in any region."""
    url = f"{moto_server_url}/eu-west-1_xyz789/.well-known/jwks.json"
    response = requests.get(url)
    assert response.status_code == 200
    data = response.json()
    assert "keys" in data
    assert len(data["keys"]) >= 1


def test_jwks_endpoint_non_default_region(moto_server_url: str):
    """JWKS endpoint should route correctly for pools in ap-southeast-1."""
    url = f"{moto_server_url}/ap-southeast-1_xyz789/.well-known/jwks.json"
    response = requests.get(url)
    assert response.status_code == 200
    data = response.json()
    assert "keys" in data
    assert len(data["keys"]) >= 1


class TestGetServiceFromUnsignedPath:
    """Unit tests for DomainDispatcherApplication.get_service_from_unsigned_path."""

    method = staticmethod(
        server.DomainDispatcherApplication.get_service_from_unsigned_path
    )

    def test_jwks_path_with_valid_pool_id(self):
        service, region = self.method("/us-east-1_abc123/.well-known/jwks.json")
        assert service == "cognito-idp"
        assert region == "us-east-1"

    def test_jwks_path_with_different_region(self):
        service, region = self.method("/eu-west-1_xyz789/.well-known/jwks.json")
        assert service == "cognito-idp"
        assert region == "eu-west-1"

    def test_jwks_path_without_underscore_in_pool_id(self):
        """Pool ID without underscore should fall back to us-east-1."""
        service, region = self.method("/nounderscore/.well-known/jwks.json")
        assert service == "cognito-idp"
        assert region == "us-east-1"

    def test_jwks_path_with_trailing_slash(self):
        service, region = self.method("/us-west-2_pool123/.well-known/jwks.json/")
        assert service == "cognito-idp"
        assert region == "us-west-2"

    def test_non_jwks_path_returns_none(self):
        service, region = self.method("/some/other/path")
        assert service is None
        assert region is None

    def test_root_path_returns_none(self):
        service, region = self.method("/")
        assert service is None
        assert region is None

    def test_empty_pool_id_jwks_path(self):
        """Bare /.well-known/jwks.json with no pool id segment."""
        service, region = self.method("/.well-known/jwks.json")
        assert service == "cognito-idp"
        # .well-known has no underscore, so falls back to us-east-1
        assert region == "us-east-1"
