from __future__ import unicode_literals

import boto3

from moto import mock_secretsmanager
from botocore.exceptions import ClientError
import sure  # noqa
import string
import unittest
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
def test_get_secret_with_mismatched_id():
    conn = boto3.client('secretsmanager', region_name='us-west-2')
    create_secret = conn.create_secret(Name='java-util-test-password',
                                       SecretString="foosecret")

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

@mock_secretsmanager
def test_get_random_password_default_length():
    conn = boto3.client('secretsmanager', region_name='us-west-2')

    random_password = conn.get_random_password()
    assert len(random_password['RandomPassword']) == 32

@mock_secretsmanager
def test_get_random_password_default_requirements():
    # When require_each_included_type, default true
    conn = boto3.client('secretsmanager', region_name='us-west-2')

    random_password = conn.get_random_password()
    # Should contain lowercase, upppercase, digit, special character
    assert any(c.islower() for c in random_password['RandomPassword'])
    assert any(c.isupper() for c in random_password['RandomPassword'])
    assert any(c.isdigit() for c in random_password['RandomPassword'])
    assert any(c in string.punctuation
               for c in random_password['RandomPassword'])

@mock_secretsmanager
def test_get_random_password_custom_length():
    conn = boto3.client('secretsmanager', region_name='us-west-2')

    random_password = conn.get_random_password(PasswordLength=50)
    assert len(random_password['RandomPassword']) == 50

@mock_secretsmanager
def test_get_random_exclude_lowercase():
    conn = boto3.client('secretsmanager', region_name='us-west-2')

    random_password = conn.get_random_password(PasswordLength=55,
                                               ExcludeLowercase=True)
    assert any(c.islower() for c in random_password['RandomPassword']) == False

@mock_secretsmanager
def test_get_random_exclude_uppercase():
    conn = boto3.client('secretsmanager', region_name='us-west-2')

    random_password = conn.get_random_password(PasswordLength=55,
                                               ExcludeUppercase=True)
    assert any(c.isupper() for c in random_password['RandomPassword']) == False

@mock_secretsmanager
def test_get_random_exclude_characters_and_symbols():
    conn = boto3.client('secretsmanager', region_name='us-west-2')

    random_password = conn.get_random_password(PasswordLength=20,
                                               ExcludeCharacters='xyzDje@?!.')
    assert any(c in 'xyzDje@?!.' for c in random_password['RandomPassword']) == False

@mock_secretsmanager
def test_get_random_exclude_numbers():
    conn = boto3.client('secretsmanager', region_name='us-west-2')

    random_password = conn.get_random_password(PasswordLength=100,
                                               ExcludeNumbers=True)
    assert any(c.isdigit() for c in random_password['RandomPassword']) == False

@mock_secretsmanager
def test_get_random_exclude_punctuation():
    conn = boto3.client('secretsmanager', region_name='us-west-2')

    random_password = conn.get_random_password(PasswordLength=100,
                                               ExcludePunctuation=True)
    assert any(c in string.punctuation
               for c in random_password['RandomPassword']) == False

@mock_secretsmanager
def test_get_random_include_space_false():
    conn = boto3.client('secretsmanager', region_name='us-west-2')

    random_password = conn.get_random_password(PasswordLength=300)
    assert any(c.isspace() for c in random_password['RandomPassword']) == False

@mock_secretsmanager
def test_get_random_include_space_true():
    conn = boto3.client('secretsmanager', region_name='us-west-2')

    random_password = conn.get_random_password(PasswordLength=4,
                                               IncludeSpace=True)
    assert any(c.isspace() for c in random_password['RandomPassword']) == True

@mock_secretsmanager
def test_get_random_require_each_included_type():
    conn = boto3.client('secretsmanager', region_name='us-west-2')

    random_password = conn.get_random_password(PasswordLength=4,
                                               RequireEachIncludedType=True)
    assert any(c in string.punctuation for c in random_password['RandomPassword']) == True
    assert any(c in string.ascii_lowercase for c in random_password['RandomPassword']) == True
    assert any(c in string.ascii_uppercase for c in random_password['RandomPassword']) == True
    assert any(c in string.digits for c in random_password['RandomPassword']) == True

@mock_secretsmanager
def test_get_random_too_short_password():
    conn = boto3.client('secretsmanager', region_name='us-west-2')

    with assert_raises(ClientError):
        random_password = conn.get_random_password(PasswordLength=3)

@mock_secretsmanager
def test_get_random_too_long_password():
    conn = boto3.client('secretsmanager', region_name='us-west-2')

    with assert_raises(Exception):
        random_password = conn.get_random_password(PasswordLength=5555)

@mock_secretsmanager
def test_describe_secret():
    conn = boto3.client('secretsmanager', region_name='us-west-2')
    conn.create_secret(Name='test-secret',
                       SecretString='foosecret')
    
    secret_description = conn.describe_secret(SecretId='test-secret')
    assert secret_description   # Returned dict is not empty
    assert secret_description['ARN'] == (
        'arn:aws:secretsmanager:us-west-2:1234567890:secret:test-secret-rIjad')

@mock_secretsmanager
def test_describe_secret_that_does_not_exist():
    conn = boto3.client('secretsmanager', region_name='us-west-2')

    with assert_raises(ClientError):
        result = conn.get_secret_value(SecretId='i-dont-exist')

@mock_secretsmanager
def test_describe_secret_that_does_not_match():
    conn = boto3.client('secretsmanager', region_name='us-west-2')
    conn.create_secret(Name='test-secret',
                       SecretString='foosecret')
    
    with assert_raises(ClientError):
        result = conn.get_secret_value(SecretId='i-dont-match')
