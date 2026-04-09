import json

import moto.server as server
from moto import mock_aws
from moto.utilities.constants import APPLICATION_AMZ_JSON_1_1

"""
Test the different server responses
"""


@mock_aws
def test_create_identity_pool():
    backend = server.create_backend_app("cognito-identity")
    test_client = backend.test_client()

    res = test_client.post(
        "/",
        json={"IdentityPoolName": "test", "AllowUnauthenticatedIdentities": True},
        headers={
            "X-Amz-Target": "AWSCognitoIdentityService.CreateIdentityPool",
            "Content-Type": APPLICATION_AMZ_JSON_1_1,
        },
    )

    json_data = json.loads(res.data.decode("utf-8"))
    assert json_data["IdentityPoolName"] == "test"


@mock_aws
def test_get_id():
    backend = server.create_backend_app("cognito-identity")
    test_client = backend.test_client()

    res = test_client.post(
        "/",
        json={"IdentityPoolName": "test", "AllowUnauthenticatedIdentities": True},
        headers={
            "X-Amz-Target": "AWSCognitoIdentityService.CreateIdentityPool",
            "Content-Type": APPLICATION_AMZ_JSON_1_1,
        },
    )

    json_data = json.loads(res.data.decode("utf-8"))
    res = test_client.post(
        "/",
        json={
            "AccountId": "someaccount",
            "IdentityPoolId": json_data["IdentityPoolId"],
            "Logins": {"someurl": "12345"},
        },
        headers={
            "X-Amz-Target": "AWSCognitoIdentityService.GetId",
            "Content-Type": APPLICATION_AMZ_JSON_1_1,
        },
    )

    json_data = json.loads(res.data.decode("utf-8"))
    assert ":" in json_data["IdentityId"]


@mock_aws
def test_list_identities():
    backend = server.create_backend_app("cognito-identity")
    test_client = backend.test_client()

    res = test_client.post(
        "/",
        json={"IdentityPoolName": "test", "AllowUnauthenticatedIdentities": True},
        headers={
            "X-Amz-Target": "AWSCognitoIdentityService.CreateIdentityPool",
            "Content-Type": APPLICATION_AMZ_JSON_1_1,
        },
    )

    json_data = json.loads(res.data.decode("utf-8"))
    identity_pool_id = json_data["IdentityPoolId"]
    res = test_client.post(
        "/",
        json={
            "AccountId": "someaccount",
            "IdentityPoolId": identity_pool_id,
            "Logins": {"someurl": "12345"},
        },
        headers={
            "X-Amz-Target": "AWSCognitoIdentityService.GetId",
            "Content-Type": APPLICATION_AMZ_JSON_1_1,
        },
    )

    json_data = json.loads(res.data.decode("utf-8"))
    identity_id = json_data["IdentityId"]

    res = test_client.post(
        "/",
        json={"IdentityPoolId": identity_pool_id},
        headers={
            "X-Amz-Target": "AWSCognitoIdentityService.ListIdentities",
            "Content-Type": APPLICATION_AMZ_JSON_1_1,
        },
    )

    json_data = json.loads(res.data.decode("utf-8"))
    assert "IdentityPoolId" in json_data and "Identities" in json_data
    assert identity_id in [x["IdentityId"] for x in json_data["Identities"]]
