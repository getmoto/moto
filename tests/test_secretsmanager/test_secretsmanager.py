from __future__ import unicode_literals

import boto3

from moto import mock_secretsmanager
from botocore.exceptions import ClientError
import sure  # noqa
from nose.tools import assert_raises

@mock_secretsmanager
def test_get_secret_value():
    conn = boto3.client('secretsmanager', region_name='us-west-2')

    create_secret = conn.create_secret(Name='java-util-test-password',
                                       SecretString="foosecret")
    result = conn.get_secret_value(SecretId='java-util-test-password')
    assert result['SecretString'] == 'foosecret'

@mock_secretsmanager
def test_get_secret_that_does_not_exist():
    conn = boto3.client('secretsmanager', region_name='us-west-2')

    with assert_raises(ClientError):
        result = conn.get_secret_value(SecretId='i-dont-exist')

@mock_secretsmanager
def test_create_secret():
    conn = boto3.client('secretsmanager', region_name='us-east-1')

    result = conn.create_secret(Name='test-secret', SecretString="foosecret")
    assert result['ARN'] == (
        'arn:aws:secretsmanager:us-east-1:1234567890:secret:test-secret-rIjad')
    assert result['Name'] == 'test-secret'
    secret = conn.get_secret_value(SecretId='test-secret')
    assert secret['SecretString'] == 'foosecret'
