import json

import moto.server as server


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
    assert data["UserPoolId"] == user_pool_id
    assert data["Username"] == "test@gmail.com"
    assert data["UserStatus"] == "CONFIRMED"


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
