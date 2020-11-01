# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
import sure  # noqa

import moto.server as server
from moto import mock_secretsmanager

"""
Test the different server responses for secretsmanager
"""

DEFAULT_SECRET_NAME = "test-secret"


@mock_secretsmanager
def test_get_secret_value():

    backend = server.create_backend_app("secretsmanager")
    test_client = backend.test_client()

    create_secret = test_client.post(
        "/",
        data={"Name": DEFAULT_SECRET_NAME, "SecretString": "foo-secret"},
        headers={"X-Amz-Target": "secretsmanager.CreateSecret"},
    )
    get_secret = test_client.post(
        "/",
        data={"SecretId": DEFAULT_SECRET_NAME, "VersionStage": "AWSCURRENT"},
        headers={"X-Amz-Target": "secretsmanager.GetSecretValue"},
    )

    json_data = json.loads(get_secret.data.decode("utf-8"))

    assert json_data["SecretString"] == "foo-secret"


@mock_secretsmanager
def test_get_secret_that_does_not_exist():

    backend = server.create_backend_app("secretsmanager")
    test_client = backend.test_client()

    get_secret = test_client.post(
        "/",
        data={"SecretId": "i-dont-exist", "VersionStage": "AWSCURRENT"},
        headers={"X-Amz-Target": "secretsmanager.GetSecretValue"},
    )
    json_data = json.loads(get_secret.data.decode("utf-8"))
    assert json_data["message"] == "Secrets Manager can't find the specified secret."
    assert json_data["__type"] == "ResourceNotFoundException"


@mock_secretsmanager
def test_get_secret_that_does_not_match():
    backend = server.create_backend_app("secretsmanager")
    test_client = backend.test_client()

    create_secret = test_client.post(
        "/",
        data={"Name": DEFAULT_SECRET_NAME, "SecretString": "foo-secret"},
        headers={"X-Amz-Target": "secretsmanager.CreateSecret"},
    )
    get_secret = test_client.post(
        "/",
        data={"SecretId": "i-dont-match", "VersionStage": "AWSCURRENT"},
        headers={"X-Amz-Target": "secretsmanager.GetSecretValue"},
    )
    json_data = json.loads(get_secret.data.decode("utf-8"))
    assert json_data["message"] == "Secrets Manager can't find the specified secret."
    assert json_data["__type"] == "ResourceNotFoundException"


@mock_secretsmanager
def test_get_secret_that_has_no_value():
    backend = server.create_backend_app("secretsmanager")
    test_client = backend.test_client()

    create_secret = test_client.post(
        "/",
        data={"Name": DEFAULT_SECRET_NAME},
        headers={"X-Amz-Target": "secretsmanager.CreateSecret"},
    )
    get_secret = test_client.post(
        "/",
        data={"SecretId": DEFAULT_SECRET_NAME},
        headers={"X-Amz-Target": "secretsmanager.GetSecretValue"},
    )

    json_data = json.loads(get_secret.data.decode("utf-8"))
    assert (
        json_data["message"]
        == "Secrets Manager can't find the specified secret value for staging label: AWSCURRENT"
    )
    assert json_data["__type"] == "ResourceNotFoundException"


@mock_secretsmanager
def test_create_secret():

    backend = server.create_backend_app("secretsmanager")
    test_client = backend.test_client()

    res = test_client.post(
        "/",
        data={"Name": "test-secret", "SecretString": "foo-secret"},
        headers={"X-Amz-Target": "secretsmanager.CreateSecret"},
    )
    res_2 = test_client.post(
        "/",
        data={"Name": "test-secret-2", "SecretString": "bar-secret"},
        headers={"X-Amz-Target": "secretsmanager.CreateSecret"},
    )

    json_data = json.loads(res.data.decode("utf-8"))
    assert json_data["ARN"] != ""
    assert json_data["Name"] == "test-secret"

    json_data_2 = json.loads(res_2.data.decode("utf-8"))
    assert json_data_2["ARN"] != ""
    assert json_data_2["Name"] == "test-secret-2"


@mock_secretsmanager
def test_describe_secret():

    backend = server.create_backend_app("secretsmanager")
    test_client = backend.test_client()

    create_secret = test_client.post(
        "/",
        data={"Name": "test-secret", "SecretString": "foosecret"},
        headers={"X-Amz-Target": "secretsmanager.CreateSecret"},
    )
    describe_secret = test_client.post(
        "/",
        data={"SecretId": "test-secret"},
        headers={"X-Amz-Target": "secretsmanager.DescribeSecret"},
    )

    create_secret_2 = test_client.post(
        "/",
        data={"Name": "test-secret-2", "SecretString": "barsecret"},
        headers={"X-Amz-Target": "secretsmanager.CreateSecret"},
    )
    describe_secret_2 = test_client.post(
        "/",
        data={"SecretId": "test-secret-2"},
        headers={"X-Amz-Target": "secretsmanager.DescribeSecret"},
    )

    json_data = json.loads(describe_secret.data.decode("utf-8"))
    assert json_data  # Returned dict is not empty
    assert json_data["ARN"] != ""
    assert json_data["Name"] == "test-secret"

    json_data_2 = json.loads(describe_secret_2.data.decode("utf-8"))
    assert json_data_2  # Returned dict is not empty
    assert json_data_2["ARN"] != ""
    assert json_data_2["Name"] == "test-secret-2"


@mock_secretsmanager
def test_describe_secret_that_does_not_exist():

    backend = server.create_backend_app("secretsmanager")
    test_client = backend.test_client()

    describe_secret = test_client.post(
        "/",
        data={"SecretId": "i-dont-exist"},
        headers={"X-Amz-Target": "secretsmanager.DescribeSecret"},
    )

    json_data = json.loads(describe_secret.data.decode("utf-8"))
    assert json_data["message"] == "Secrets Manager can't find the specified secret."
    assert json_data["__type"] == "ResourceNotFoundException"


@mock_secretsmanager
def test_describe_secret_that_does_not_match():

    backend = server.create_backend_app("secretsmanager")
    test_client = backend.test_client()

    create_secret = test_client.post(
        "/",
        data={"Name": DEFAULT_SECRET_NAME, "SecretString": "foosecret"},
        headers={"X-Amz-Target": "secretsmanager.CreateSecret"},
    )
    describe_secret = test_client.post(
        "/",
        data={"SecretId": "i-dont-match"},
        headers={"X-Amz-Target": "secretsmanager.DescribeSecret"},
    )

    json_data = json.loads(describe_secret.data.decode("utf-8"))
    assert json_data["message"] == "Secrets Manager can't find the specified secret."
    assert json_data["__type"] == "ResourceNotFoundException"


@mock_secretsmanager
def test_rotate_secret():
    backend = server.create_backend_app("secretsmanager")
    test_client = backend.test_client()

    create_secret = test_client.post(
        "/",
        data={"Name": DEFAULT_SECRET_NAME, "SecretString": "foosecret"},
        headers={"X-Amz-Target": "secretsmanager.CreateSecret"},
    )

    client_request_token = "EXAMPLE2-90ab-cdef-fedc-ba987SECRET2"
    rotate_secret = test_client.post(
        "/",
        data={
            "SecretId": DEFAULT_SECRET_NAME,
            "ClientRequestToken": client_request_token,
        },
        headers={"X-Amz-Target": "secretsmanager.RotateSecret"},
    )

    json_data = json.loads(rotate_secret.data.decode("utf-8"))
    assert json_data  # Returned dict is not empty
    assert json_data["ARN"] != ""
    assert json_data["Name"] == DEFAULT_SECRET_NAME
    assert json_data["VersionId"] == client_request_token


# @mock_secretsmanager
# def test_rotate_secret_enable_rotation():
#     backend = server.create_backend_app('secretsmanager')
#     test_client = backend.test_client()

#     create_secret = test_client.post(
#                         '/',
#                         data={
#                             "Name": "test-secret",
#                             "SecretString": "foosecret"
#                         },
#                         headers={
#                             "X-Amz-Target": "secretsmanager.CreateSecret"
#                         },
#                     )

#     initial_description = test_client.post(
#                             '/',
#                             data={
#                                 "SecretId": "test-secret"
#                             },
#                             headers={
#                                 "X-Amz-Target": "secretsmanager.DescribeSecret"
#                             },
#                           )

#     json_data = json.loads(initial_description.data.decode("utf-8"))
#     assert json_data   # Returned dict is not empty
#     assert json_data['RotationEnabled'] is False
#     assert json_data['RotationRules']['AutomaticallyAfterDays'] == 0

#     rotate_secret = test_client.post(
#                         '/',
#                         data={
#                             "SecretId": "test-secret",
#                             "RotationRules": {"AutomaticallyAfterDays": 42}
#                         },
#                         headers={
#                             "X-Amz-Target": "secretsmanager.RotateSecret"
#                         },
#                     )

#     rotated_description = test_client.post(
#                             '/',
#                             data={
#                                 "SecretId": "test-secret"
#                             },
#                             headers={
#                                 "X-Amz-Target": "secretsmanager.DescribeSecret"
#                             },
#                           )

#     json_data = json.loads(rotated_description.data.decode("utf-8"))
#     assert json_data   # Returned dict is not empty
#     assert json_data['RotationEnabled'] is True
#     assert json_data['RotationRules']['AutomaticallyAfterDays'] == 42


@mock_secretsmanager
def test_rotate_secret_that_does_not_exist():
    backend = server.create_backend_app("secretsmanager")
    test_client = backend.test_client()

    rotate_secret = test_client.post(
        "/",
        data={"SecretId": "i-dont-exist"},
        headers={"X-Amz-Target": "secretsmanager.RotateSecret"},
    )

    json_data = json.loads(rotate_secret.data.decode("utf-8"))
    assert json_data["message"] == "Secrets Manager can't find the specified secret."
    assert json_data["__type"] == "ResourceNotFoundException"


@mock_secretsmanager
def test_rotate_secret_that_does_not_match():
    backend = server.create_backend_app("secretsmanager")
    test_client = backend.test_client()

    create_secret = test_client.post(
        "/",
        data={"Name": DEFAULT_SECRET_NAME, "SecretString": "foosecret"},
        headers={"X-Amz-Target": "secretsmanager.CreateSecret"},
    )

    rotate_secret = test_client.post(
        "/",
        data={"SecretId": "i-dont-match"},
        headers={"X-Amz-Target": "secretsmanager.RotateSecret"},
    )

    json_data = json.loads(rotate_secret.data.decode("utf-8"))
    assert json_data["message"] == "Secrets Manager can't find the specified secret."
    assert json_data["__type"] == "ResourceNotFoundException"


@mock_secretsmanager
def test_rotate_secret_client_request_token_too_short():
    backend = server.create_backend_app("secretsmanager")
    test_client = backend.test_client()

    create_secret = test_client.post(
        "/",
        data={"Name": DEFAULT_SECRET_NAME, "SecretString": "foosecret"},
        headers={"X-Amz-Target": "secretsmanager.CreateSecret"},
    )

    client_request_token = "ED9F8B6C-85B7-B7E4-38F2A3BEB13C"
    rotate_secret = test_client.post(
        "/",
        data={
            "SecretId": DEFAULT_SECRET_NAME,
            "ClientRequestToken": client_request_token,
        },
        headers={"X-Amz-Target": "secretsmanager.RotateSecret"},
    )

    json_data = json.loads(rotate_secret.data.decode("utf-8"))
    assert json_data["message"] == "ClientRequestToken must be 32-64 characters long."
    assert json_data["__type"] == "InvalidParameterException"


@mock_secretsmanager
def test_rotate_secret_client_request_token_too_long():
    backend = server.create_backend_app("secretsmanager")
    test_client = backend.test_client()

    create_secret = test_client.post(
        "/",
        data={"Name": DEFAULT_SECRET_NAME, "SecretString": "foosecret"},
        headers={"X-Amz-Target": "secretsmanager.CreateSecret"},
    )

    client_request_token = (
        "ED9F8B6C-85B7-446A-B7E4-38F2A3BEB13C-" "ED9F8B6C-85B7-446A-B7E4-38F2A3BEB13C"
    )
    rotate_secret = test_client.post(
        "/",
        data={
            "SecretId": DEFAULT_SECRET_NAME,
            "ClientRequestToken": client_request_token,
        },
        headers={"X-Amz-Target": "secretsmanager.RotateSecret"},
    )

    json_data = json.loads(rotate_secret.data.decode("utf-8"))
    assert json_data["message"] == "ClientRequestToken must be 32-64 characters long."
    assert json_data["__type"] == "InvalidParameterException"


@mock_secretsmanager
def test_rotate_secret_rotation_lambda_arn_too_long():
    backend = server.create_backend_app("secretsmanager")
    test_client = backend.test_client()

    create_secret = test_client.post(
        "/",
        data={"Name": DEFAULT_SECRET_NAME, "SecretString": "foosecret"},
        headers={"X-Amz-Target": "secretsmanager.CreateSecret"},
    )

    rotation_lambda_arn = "85B7-446A-B7E4" * 147  # == 2058 characters
    rotate_secret = test_client.post(
        "/",
        data={
            "SecretId": DEFAULT_SECRET_NAME,
            "RotationLambdaARN": rotation_lambda_arn,
        },
        headers={"X-Amz-Target": "secretsmanager.RotateSecret"},
    )

    json_data = json.loads(rotate_secret.data.decode("utf-8"))
    assert json_data["message"] == "RotationLambdaARN must <= 2048 characters long."
    assert json_data["__type"] == "InvalidParameterException"


@mock_secretsmanager
def test_put_secret_value_puts_new_secret():
    backend = server.create_backend_app("secretsmanager")
    test_client = backend.test_client()
    test_client.post(
        "/",
        data={"Name": DEFAULT_SECRET_NAME, "SecretString": "foosecret"},
        headers={"X-Amz-Target": "secretsmanager.CreateSecret"},
    )
    test_client.post(
        "/",
        data={
            "SecretId": DEFAULT_SECRET_NAME,
            "SecretString": "foosecret",
            "VersionStages": ["AWSCURRENT"],
        },
        headers={"X-Amz-Target": "secretsmanager.PutSecretValue"},
    )

    put_second_secret_value_json = test_client.post(
        "/",
        data={
            "SecretId": DEFAULT_SECRET_NAME,
            "SecretString": "foosecret",
            "VersionStages": ["AWSCURRENT"],
        },
        headers={"X-Amz-Target": "secretsmanager.PutSecretValue"},
    )
    second_secret_json_data = json.loads(
        put_second_secret_value_json.data.decode("utf-8")
    )

    version_id = second_secret_json_data["VersionId"]

    secret_value_json = test_client.post(
        "/",
        data={
            "SecretId": DEFAULT_SECRET_NAME,
            "VersionId": version_id,
            "VersionStage": "AWSCURRENT",
        },
        headers={"X-Amz-Target": "secretsmanager.GetSecretValue"},
    )

    second_secret_json_data = json.loads(secret_value_json.data.decode("utf-8"))

    assert second_secret_json_data
    assert second_secret_json_data["SecretString"] == "foosecret"


@mock_secretsmanager
def test_put_secret_value_can_get_first_version_if_put_twice():
    backend = server.create_backend_app("secretsmanager")
    test_client = backend.test_client()

    first_secret_string = "first_secret"
    second_secret_string = "second_secret"

    test_client.post(
        "/",
        data={"Name": DEFAULT_SECRET_NAME, "SecretString": "foosecret"},
        headers={"X-Amz-Target": "secretsmanager.CreateSecret"},
    )

    put_first_secret_value_json = test_client.post(
        "/",
        data={
            "SecretId": DEFAULT_SECRET_NAME,
            "SecretString": first_secret_string,
            "VersionStages": ["AWSCURRENT"],
        },
        headers={"X-Amz-Target": "secretsmanager.PutSecretValue"},
    )

    first_secret_json_data = json.loads(
        put_first_secret_value_json.data.decode("utf-8")
    )

    first_secret_version_id = first_secret_json_data["VersionId"]

    test_client.post(
        "/",
        data={
            "SecretId": DEFAULT_SECRET_NAME,
            "SecretString": second_secret_string,
            "VersionStages": ["AWSCURRENT"],
        },
        headers={"X-Amz-Target": "secretsmanager.PutSecretValue"},
    )

    get_first_secret_value_json = test_client.post(
        "/",
        data={
            "SecretId": DEFAULT_SECRET_NAME,
            "VersionId": first_secret_version_id,
            "VersionStage": "AWSCURRENT",
        },
        headers={"X-Amz-Target": "secretsmanager.GetSecretValue"},
    )

    get_first_secret_json_data = json.loads(
        get_first_secret_value_json.data.decode("utf-8")
    )

    assert get_first_secret_json_data
    assert get_first_secret_json_data["SecretString"] == first_secret_string


@mock_secretsmanager
def test_put_secret_value_versions_differ_if_same_secret_put_twice():
    backend = server.create_backend_app("secretsmanager")
    test_client = backend.test_client()

    test_client.post(
        "/",
        data={"Name": DEFAULT_SECRET_NAME, "SecretString": "foosecret"},
        headers={"X-Amz-Target": "secretsmanager.CreateSecret"},
    )
    put_first_secret_value_json = test_client.post(
        "/",
        data={
            "SecretId": DEFAULT_SECRET_NAME,
            "SecretString": "secret",
            "VersionStages": ["AWSCURRENT"],
        },
        headers={"X-Amz-Target": "secretsmanager.PutSecretValue"},
    )
    first_secret_json_data = json.loads(
        put_first_secret_value_json.data.decode("utf-8")
    )
    first_secret_version_id = first_secret_json_data["VersionId"]

    put_second_secret_value_json = test_client.post(
        "/",
        data={
            "SecretId": DEFAULT_SECRET_NAME,
            "SecretString": "secret",
            "VersionStages": ["AWSCURRENT"],
        },
        headers={"X-Amz-Target": "secretsmanager.PutSecretValue"},
    )
    second_secret_json_data = json.loads(
        put_second_secret_value_json.data.decode("utf-8")
    )
    second_secret_version_id = second_secret_json_data["VersionId"]

    assert first_secret_version_id != second_secret_version_id


@mock_secretsmanager
def test_can_list_secret_version_ids():
    backend = server.create_backend_app("secretsmanager")
    test_client = backend.test_client()

    test_client.post(
        "/",
        data={"Name": DEFAULT_SECRET_NAME, "SecretString": "foosecret"},
        headers={"X-Amz-Target": "secretsmanager.CreateSecret"},
    )
    put_first_secret_value_json = test_client.post(
        "/",
        data={
            "SecretId": DEFAULT_SECRET_NAME,
            "SecretString": "secret",
            "VersionStages": ["AWSCURRENT"],
        },
        headers={"X-Amz-Target": "secretsmanager.PutSecretValue"},
    )
    first_secret_json_data = json.loads(
        put_first_secret_value_json.data.decode("utf-8")
    )
    first_secret_version_id = first_secret_json_data["VersionId"]
    put_second_secret_value_json = test_client.post(
        "/",
        data={
            "SecretId": DEFAULT_SECRET_NAME,
            "SecretString": "secret",
            "VersionStages": ["AWSCURRENT"],
        },
        headers={"X-Amz-Target": "secretsmanager.PutSecretValue"},
    )
    second_secret_json_data = json.loads(
        put_second_secret_value_json.data.decode("utf-8")
    )
    second_secret_version_id = second_secret_json_data["VersionId"]

    list_secret_versions_json = test_client.post(
        "/",
        data={"SecretId": DEFAULT_SECRET_NAME},
        headers={"X-Amz-Target": "secretsmanager.ListSecretVersionIds"},
    )

    versions_list = json.loads(list_secret_versions_json.data.decode("utf-8"))

    returned_version_ids = [v["VersionId"] for v in versions_list["Versions"]]

    assert [
        first_secret_version_id,
        second_secret_version_id,
    ].sort() == returned_version_ids.sort()


@mock_secretsmanager
def test_get_resource_policy_secret():

    backend = server.create_backend_app("secretsmanager")
    test_client = backend.test_client()

    create_secret = test_client.post(
        "/",
        data={"Name": "test-secret", "SecretString": "foosecret"},
        headers={"X-Amz-Target": "secretsmanager.CreateSecret"},
    )
    describe_secret = test_client.post(
        "/",
        data={"SecretId": "test-secret"},
        headers={"X-Amz-Target": "secretsmanager.GetResourcePolicy"},
    )

    json_data = json.loads(describe_secret.data.decode("utf-8"))
    assert json_data  # Returned dict is not empty
    assert json_data["ARN"] != ""
    assert json_data["Name"] == "test-secret"


#
# The following tests should work, but fail on the embedded dict in
# RotationRules. The error message suggests a problem deeper in the code, which
# needs further investigation.
#

# @mock_secretsmanager
# def test_rotate_secret_rotation_period_zero():
#     backend = server.create_backend_app('secretsmanager')
#     test_client = backend.test_client()

#     create_secret = test_client.post('/',
#                         data={"Name": "test-secret",
#                               "SecretString": "foosecret"},
#                         headers={
#                             "X-Amz-Target": "secretsmanager.CreateSecret"
#                         },
#                     )

#     rotate_secret = test_client.post('/',
#                         data={"SecretId": "test-secret",
#                               "RotationRules": {"AutomaticallyAfterDays": 0}},
#                         headers={
#                             "X-Amz-Target": "secretsmanager.RotateSecret"
#                         },
#                     )

#     json_data = json.loads(rotate_secret.data.decode("utf-8"))
#     assert json_data['message'] == "RotationRules.AutomaticallyAfterDays must be within 1-1000."
#     assert json_data['__type'] == 'InvalidParameterException'

# @mock_secretsmanager
# def test_rotate_secret_rotation_period_too_long():
#     backend = server.create_backend_app('secretsmanager')
#     test_client = backend.test_client()

#     create_secret = test_client.post('/',
#                         data={"Name": "test-secret",
#                               "SecretString": "foosecret"},
#                         headers={
#                             "X-Amz-Target": "secretsmanager.CreateSecret"
#                         },
#                     )

#     rotate_secret = test_client.post('/',
#                         data={"SecretId": "test-secret",
#                               "RotationRules": {"AutomaticallyAfterDays": 1001}},
#                         headers={
#                             "X-Amz-Target": "secretsmanager.RotateSecret"
#                         },
#                     )

#     json_data = json.loads(rotate_secret.data.decode("utf-8"))
#     assert json_data['message'] == "RotationRules.AutomaticallyAfterDays must be within 1-1000."
#     assert json_data['__type'] == 'InvalidParameterException'
