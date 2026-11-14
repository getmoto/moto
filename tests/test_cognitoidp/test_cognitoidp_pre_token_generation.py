import json
import uuid
from unittest import SkipTest
from unittest.mock import patch

import boto3
import pytest
import requests
from botocore.exceptions import ClientError

from moto import mock_aws, settings
from tests.markers import requires_docker

from ..test_awslambda.utilities import (
    PYTHON_VERSION,
    _process_lambda,
    get_role_name,
    get_test_zip_file1,
)
from .test_cognitoidp import get_jwt_payload

REGION = "us-west-2"
PASSWORD = "P2$Sword"
ROLE_ARN = "arn:aws:iam::123456789012:role/admins"

if settings.TEST_SERVER_MODE:
    raise SkipTest("Lambda config can not be passed in ServerMode")


def _create_function(zip_file=None):
    return boto3.client("lambda", REGION).create_function(
        FunctionName=str(uuid.uuid4())[:8],
        Runtime=PYTHON_VERSION,
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": zip_file or get_test_zip_file1()},
    )["FunctionArn"]


def _create_pool(lambda_config):
    conn = boto3.client("cognito-idp", REGION)
    user_pool_id = conn.create_user_pool(PoolName="pool", LambdaConfig=lambda_config)[
        "UserPool"
    ]["Id"]
    client_id = conn.create_user_pool_client(
        UserPoolId=user_pool_id,
        ClientName="client",
        ExplicitAuthFlows=["USER_PASSWORD_AUTH", "ALLOW_REFRESH_TOKEN_AUTH"],
        ReadAttributes=["email"],
    )["UserPoolClient"]["ClientId"]
    conn.create_group(
        GroupName="admins", UserPoolId=user_pool_id, RoleArn=ROLE_ARN, Precedence=1
    )
    conn.admin_create_user(
        UserPoolId=user_pool_id,
        Username="user",
        TemporaryPassword=PASSWORD,
        UserAttributes=[{"Name": "email", "Value": "user@example.com"}],
        MessageAction="SUPPRESS",
    )
    conn.admin_add_user_to_group(
        UserPoolId=user_pool_id, Username="user", GroupName="admins"
    )
    return conn, user_pool_id, client_id


def _log_in(conn, user_pool_id, client_id):
    conn.admin_set_user_password(
        UserPoolId=user_pool_id, Username="user", Password=PASSWORD, Permanent=True
    )
    tokens = conn.initiate_auth(
        ClientId=client_id,
        AuthFlow="USER_PASSWORD_AUTH",
        AuthParameters={"USERNAME": "user", "PASSWORD": PASSWORD},
    )["AuthenticationResult"]
    return (
        get_jwt_payload(tokens["IdToken"]).claims,
        get_jwt_payload(tokens["AccessToken"]).claims,
    )


def _set_lambda_responses(*responses):
    requests.post(
        "http://motoapi.amazonaws.com/moto-api/static/lambda-simple/response",
        json={
            "results": [r if isinstance(r, str) else json.dumps(r) for r in responses],
            "region": REGION,
        },
    )


@mock_aws(config={"lambda": {"use_docker": False}})
def test_pre_token_generation_event():
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("Can only test patched code in DecoratorMode")
    events = []

    def invoke(*args, **kwargs):
        events.append(json.loads(kwargs["body"]))
        return kwargs["body"]

    function_arn = _create_function()
    conn, user_pool_id, client_id = _create_pool(
        {
            "PreTokenGenerationConfig": {
                "LambdaArn": function_arn,
                "LambdaVersion": "V2_0",
            }
        }
    )
    with patch("moto.awslambda_simple.models.LambdaSimpleBackend.invoke", new=invoke):
        session = conn.initiate_auth(
            ClientId=client_id,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": "user", "PASSWORD": PASSWORD},
        )["Session"]
        refresh_token = conn.respond_to_auth_challenge(
            ClientId=client_id,
            ChallengeName="NEW_PASSWORD_REQUIRED",
            Session=session,
            ChallengeResponses={"USERNAME": "user", "NEW_PASSWORD": PASSWORD},
            ClientMetadata={"key": "challenge"},
        )["AuthenticationResult"]["RefreshToken"]
        conn.initiate_auth(
            ClientId=client_id,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": "user", "PASSWORD": PASSWORD},
            ClientMetadata={"key": "ignored"},
        )
        conn.get_tokens_from_refresh_token(
            ClientId=client_id,
            RefreshToken=refresh_token,
            ClientMetadata={"key": "refresh"},
        )

    assert [e["triggerSource"] for e in events] == [
        "TokenGeneration_NewPasswordChallenge",
        "TokenGeneration_Authentication",
        "TokenGeneration_RefreshTokens",
    ]
    # InitiateAuth does not pass on the ClientMetadata
    assert [e["request"].get("clientMetadata") for e in events] == [
        {"key": "challenge"},
        None,
        {"key": "refresh"},
    ]

    event = events[1]
    user_attributes = event["request"].pop("userAttributes")
    assert user_attributes["email"] == "user@example.com"
    assert user_attributes["cognito:user_status"] == "CONFIRMED"
    assert "sub" in user_attributes
    assert event == {
        "version": "2",
        "triggerSource": "TokenGeneration_Authentication",
        "region": REGION,
        "userPoolId": user_pool_id,
        "userName": "user",
        "callerContext": {
            "awsSdkVersion": "aws-sdk-unknown-unknown",
            "clientId": client_id,
        },
        "request": {
            "groupConfiguration": {
                "groupsToOverride": ["admins"],
                "iamRolesToOverride": [ROLE_ARN],
                "preferredRole": ROLE_ARN,
            },
            "scopes": ["aws.cognito.signin.user.admin"],
        },
        "response": {"claimsAndScopeOverrideDetails": None},
    }


@mock_aws(config={"lambda": {"use_docker": False}})
def test_pre_token_generation_without_changes():
    function_arn = _create_function()
    conn, user_pool_id, client_id = _create_pool(
        {
            "PreTokenGenerationConfig": {
                "LambdaArn": function_arn,
                "LambdaVersion": "V2_0",
            }
        }
    )

    # The Docker-less Lambda returns the event unchanged
    id_claims, access_claims = _log_in(conn, user_pool_id, client_id)

    assert id_claims["email"] == "user@example.com"
    assert id_claims["cognito:groups"] == ["admins"]
    assert access_claims["scope"] == "aws.cognito.signin.user.admin"


@mock_aws(config={"lambda": {"use_docker": False}})
def test_pre_token_generation_v2():
    function_arn = _create_function()
    conn, user_pool_id, client_id = _create_pool(
        {
            "PreTokenGenerationConfig": {
                "LambdaArn": function_arn,
                "LambdaVersion": "V2_0",
            }
        }
    )
    _set_lambda_responses(
        {
            "version": "2",
            "response": {
                "claimsAndScopeOverrideDetails": {
                    "idTokenGeneration": {
                        "claimsToAddOrOverride": {"tenant": "t1", "empty": None},
                        "claimsToSuppress": ["email"],
                    },
                    "accessTokenGeneration": {
                        "claimsToAddOrOverride": {"tenant": {"id": 1}},
                        "scopesToAdd": ["api/read", "free-text-scope"],
                        "scopesToSuppress": ["aws.cognito.signin.user.admin"],
                    },
                    "groupOverrideDetails": {
                        "groupsToOverride": ["readers"],
                        "iamRolesToOverride": ["arn:aws:iam::123456789012:role/r"],
                        "preferredRole": "arn:aws:iam::123456789012:role/r",
                    },
                }
            },
        }
    )

    id_claims, access_claims = _log_in(conn, user_pool_id, client_id)

    assert id_claims["tenant"] == "t1"
    assert "empty" not in id_claims
    assert "email" not in id_claims
    assert id_claims["cognito:groups"] == ["readers"]
    assert id_claims["cognito:roles"] == ["arn:aws:iam::123456789012:role/r"]
    assert id_claims["cognito:preferred_role"] == "arn:aws:iam::123456789012:role/r"

    assert access_claims["tenant"] == {"id": 1}
    assert access_claims["scope"] == "free-text-scope api/read"
    assert access_claims["cognito:groups"] == ["readers"]
    assert "cognito:roles" not in access_claims


@mock_aws(config={"lambda": {"use_docker": False}})
def test_pre_token_generation_ignores_protected_claims():
    function_arn = _create_function()
    conn, user_pool_id, client_id = _create_pool(
        {
            "PreTokenGenerationConfig": {
                "LambdaArn": function_arn,
                "LambdaVersion": "V2_0",
            }
        }
    )
    overrides = {
        "claimsToAddOrOverride": {
            "iss": "other",
            "token_use": "other",
            "cognito:groups": ["other"],
            "scope": "other",
        },
        "claimsToSuppress": ["sub", "exp"],
    }
    _set_lambda_responses(
        {
            "version": "2",
            "response": {
                "claimsAndScopeOverrideDetails": {
                    "idTokenGeneration": overrides,
                    "accessTokenGeneration": overrides,
                }
            },
        }
    )

    id_claims, access_claims = _log_in(conn, user_pool_id, client_id)

    for claims in (id_claims, access_claims):
        assert claims["iss"].startswith("https://cognito-idp.")
        assert claims["cognito:groups"] == ["admins"]
        assert "sub" in claims
        assert "exp" in claims
    assert id_claims["token_use"] == "id"
    assert access_claims["token_use"] == "access"
    # Only reserved in the access token
    assert id_claims["scope"] == "other"
    assert access_claims["scope"] == "aws.cognito.signin.user.admin"


@pytest.mark.parametrize(
    "lambda_config",
    [
        "legacy",
        "V1_0",
    ],
)
@mock_aws(config={"lambda": {"use_docker": False}})
def test_pre_token_generation_v1(lambda_config):
    function_arn = _create_function()
    conn, user_pool_id, client_id = _create_pool(
        {"PreTokenGeneration": function_arn}
        if lambda_config == "legacy"
        else {
            "PreTokenGenerationConfig": {
                "LambdaArn": function_arn,
                "LambdaVersion": lambda_config,
            }
        }
    )
    _set_lambda_responses(
        {
            "version": "1",
            "response": {
                "claimsOverrideDetails": {
                    "claimsToAddOrOverride": {
                        "number": 1,
                        "flag": True,
                        "text": "t",
                        "empty": None,
                    },
                    "claimsToSuppress": ["email"],
                    "groupOverrideDetails": {"groupsToOverride": []},
                }
            },
        }
    )

    id_claims, access_claims = _log_in(conn, user_pool_id, client_id)

    assert id_claims["number"] == "1"
    assert id_claims["flag"] == "true"
    assert id_claims["text"] == "t"
    assert "empty" not in id_claims
    assert "email" not in id_claims
    assert "cognito:groups" not in id_claims

    assert "text" not in access_claims
    assert "cognito:groups" not in access_claims


@pytest.mark.parametrize(
    "version,response,message",
    [
        ("V2_0", "null", "Invalid lambda function output : Invalid JSON"),
        ("V2_0", '"text"', "Unrecognizable lambda output"),
        ("V2_0", {"foo": 1}, "Invalid version in Lambda response. Version should be 2"),
        (
            "V2_0",
            {
                "version": "2",
                "response": {
                    "claimsAndScopeOverrideDetails": {
                        "accessTokenGeneration": {"claimsToAddOrOverride": ["a"]}
                    }
                },
            },
            "Unrecognizable lambda output",
        ),
        ("V1_0", {"foo": 1}, "Invalid version in Lambda response. Version should be 1"),
        (
            "V1_0",
            {
                "version": "1",
                "response": {
                    "claimsOverrideDetails": {
                        "claimsToAddOrOverride": {"object": {"a": 1}}
                    }
                },
            },
            "Unrecognizable lambda output",
        ),
    ],
)
@mock_aws(config={"lambda": {"use_docker": False}})
def test_pre_token_generation_invalid_response(version, response, message):
    function_arn = _create_function()
    conn, user_pool_id, client_id = _create_pool(
        {
            "PreTokenGenerationConfig": {
                "LambdaArn": function_arn,
                "LambdaVersion": version,
            }
        }
    )
    _set_lambda_responses(response)

    with pytest.raises(ClientError) as exc:
        _log_in(conn, user_pool_id, client_id)
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidLambdaResponseException"
    assert err["Message"] == message


@pytest.mark.parametrize(
    "lambda_config,trigger_name",
    [
        ("legacy", "PreTokenGeneration"),
        ("V2_0", "PreTokenGenerationV2_0"),
    ],
)
@mock_aws(config={"lambda": {"use_docker": False}})
def test_pre_token_generation_unknown_function(lambda_config, trigger_name):
    function_arn = f"arn:aws:lambda:{REGION}:123456789012:function:unknown"
    conn, user_pool_id, client_id = _create_pool(
        {"PreTokenGeneration": function_arn}
        if lambda_config == "legacy"
        else {
            "PreTokenGenerationConfig": {
                "LambdaArn": function_arn,
                "LambdaVersion": lambda_config,
            }
        }
    )

    with pytest.raises(ClientError) as exc:
        _log_in(conn, user_pool_id, client_id)
    err = exc.value.response["Error"]
    assert err["Code"] == "UnexpectedLambdaException"
    assert (
        err["Message"]
        == f"{trigger_name} invocation failed due to error AccessDeniedException."
    )


@requires_docker
@mock_aws
def test_pre_token_generation_function_error():
    function_arn = _create_function(
        _process_lambda(
            "def lambda_handler(event, context):\n    raise Exception('Not allowed')"
        )
    )
    conn, user_pool_id, client_id = _create_pool(
        {
            "PreTokenGenerationConfig": {
                "LambdaArn": function_arn,
                "LambdaVersion": "V2_0",
            }
        }
    )

    with pytest.raises(ClientError) as exc:
        _log_in(conn, user_pool_id, client_id)
    err = exc.value.response["Error"]
    assert err["Code"] == "UserLambdaValidationException"
    assert err["Message"] == "PreTokenGenerationV2_0 failed with error Not allowed."
