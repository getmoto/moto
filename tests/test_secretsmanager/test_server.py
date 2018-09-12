from __future__ import unicode_literals

import json
import sure  # noqa

import moto.server as server
from moto import mock_secretsmanager

'''
Test the different server responses for secretsmanager
'''


@mock_secretsmanager
def test_get_secret_value():

    backend = server.create_backend_app("secretsmanager")
    test_client = backend.test_client()

    create_secret = test_client.post('/',
                           data={"Name": "test-secret",
                                 "SecretString": "foo-secret"},
                           headers={
                               "X-Amz-Target": "secretsmanager.CreateSecret"},
                           )
    get_secret = test_client.post('/',
                           data={"SecretId": "test-secret",
                                 "VersionStage": "AWSCURRENT"},
                           headers={
                               "X-Amz-Target": "secretsmanager.GetSecretValue"},
                           )

    json_data = json.loads(get_secret.data.decode("utf-8"))
    assert json_data['SecretString'] == 'foo-secret'

@mock_secretsmanager
def test_get_secret_that_does_not_exist():

    backend = server.create_backend_app("secretsmanager")
    test_client = backend.test_client()

    get_secret = test_client.post('/',
                           data={"SecretId": "i-dont-exist",
                                 "VersionStage": "AWSCURRENT"},
                           headers={
                               "X-Amz-Target": "secretsmanager.GetSecretValue"},
                           )
    json_data = json.loads(get_secret.data.decode("utf-8"))
    assert json_data['message'] == "Secrets Manager can't find the specified secret"
    assert json_data['__type'] == 'ResourceNotFoundException'

@mock_secretsmanager
def test_create_secret():

    backend = server.create_backend_app("secretsmanager")
    test_client = backend.test_client()

    res = test_client.post('/',
                           data={"Name": "test-secret",
                                 "SecretString": "foo-secret"},
                           headers={
                               "X-Amz-Target": "secretsmanager.CreateSecret"},
                           )

    json_data = json.loads(res.data.decode("utf-8"))
    assert json_data['ARN'] == (
        'arn:aws:secretsmanager:us-east-1:1234567890:secret:test-secret-rIjad')
    assert json_data['Name'] == 'test-secret'

@mock_secretsmanager
def test_describe_secret():

    backend = server.create_backend_app('secretsmanager')
    test_client = backend.test_client()

    create_secret = test_client.post('/',
                        data={"Name": "test-secret",
                              "SecretString": "foosecret"},
                        headers={
                            "X-Amz-Target": "secretsmanager.CreateSecret"
                        },
                    )
    describe_secret = test_client.post('/',
                        data={"SecretId": "test-secret"},
                        headers={
                            "X-Amz-Target": "secretsmanager.DescribeSecret"
                        },
                    )

    json_data = json.loads(describe_secret.data.decode("utf-8"))
    assert json_data   # Returned dict is not empty
    assert json_data['ARN'] == (
        'arn:aws:secretsmanager:us-east-1:1234567890:secret:test-secret-rIjad'
    )

@mock_secretsmanager
def test_describe_secret_that_does_not_exist():

    backend = server.create_backend_app('secretsmanager')
    test_client = backend.test_client()

    describe_secret = test_client.post('/',
                        data={"SecretId": "i-dont-exist"},
                        headers={
                            "X-Amz-Target": "secretsmanager.DescribeSecret"
                        },
                    )

    json_data = json.loads(describe_secret.data.decode("utf-8"))
    assert json_data['message'] == "Secrets Manager can't find the specified secret"
    assert json_data['__type'] == 'ResourceNotFoundException'

@mock_secretsmanager
def test_describe_secret_that_does_not_match():

    backend = server.create_backend_app('secretsmanager')
    test_client = backend.test_client()

    create_secret = test_client.post('/',
                        data={"Name": "test-secret",
                              "SecretString": "foosecret"},
                        headers={
                            "X-Amz-Target": "secretsmanager.CreateSecret"
                        },
                    )
    describe_secret = test_client.post('/',
                        data={"SecretId": "i-dont-match"},
                        headers={
                            "X-Amz-Target": "secretsmanager.DescribeSecret"
                        },
                    )

    json_data = json.loads(describe_secret.data.decode("utf-8"))
    assert json_data['message'] == "Secrets Manager can't find the specified secret"
    assert json_data['__type'] == 'ResourceNotFoundException'
