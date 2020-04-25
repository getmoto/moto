from __future__ import unicode_literals

import json
import sure  # noqa

import moto.server as server
from moto import mock_cognitoidentity

"""
Test the different server responses
"""


@mock_cognitoidentity
def test_create_identity_pool():

    backend = server.create_backend_app("cognito-identity")
    test_client = backend.test_client()

    res = test_client.post(
        "/",
        data={"IdentityPoolName": "test", "AllowUnauthenticatedIdentities": True},
        headers={
            "X-Amz-Target": "com.amazonaws.cognito.identity.model.AWSCognitoIdentityService.CreateIdentityPool"
        },
    )

    json_data = json.loads(res.data.decode("utf-8"))
    assert json_data["IdentityPoolName"] == "test"


@mock_cognitoidentity
def test_get_id():
    backend = server.create_backend_app("cognito-identity")
    test_client = backend.test_client()

    res = test_client.post(
        "/",
        data=json.dumps(
            {
                "AccountId": "someaccount",
                "IdentityPoolId": "us-west-2:12345",
                "Logins": {"someurl": "12345"},
            }
        ),
        headers={
            "X-Amz-Target": "com.amazonaws.cognito.identity.model.AWSCognitoIdentityService.GetId"
        },
    )

    json_data = json.loads(res.data.decode("utf-8"))
    assert ":" in json_data["IdentityId"]
