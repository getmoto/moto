from __future__ import unicode_literals

import boto3

from moto import mock_secretsmanager
import sure  # noqa

@mock_secretsmanager
def test_get_secret_value():
    conn = boto3.client('secretsmanager', region_name='us-west-2')

    result = conn.get_secret_value(SecretId='java-util-test-password')
    assert result['SecretString'] == 'mysecretstring'
