import json
import moto.server as server


def test_sign_up_method_without_authentication():
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
    json.loads(res.data)["UserPoolClients"].should.have.length_of(1)

    # Sign Up User
    data = {"ClientId": client_id, "Username": "test@gmail.com", "Password": "12345678"}
    res = test_client.post(
        "/",
        data=json.dumps(data),
        headers={"X-Amz-Target": "AWSCognitoIdentityProviderService.SignUp"},
    )
    res.status_code.should.equal(200)
    json.loads(res.data).should.have.key("UserConfirmed").equals(False)
