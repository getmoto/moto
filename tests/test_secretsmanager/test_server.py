from __future__ import unicode_literals

import json
import sure  # noqa

import moto.server as server
from moto import mock_secretsmanager

'''
Test the different server responses
'''


@mock_secretsmanager
def test_get_secret_value():

    backend = server.create_backend_app("secretsmanager-get-secret-value")
    test_client = backend.test_client()

    res = test_client.post('/',
                           data={"SecretId": "test", "VersionStage": "AWSCURRENT"},
                           headers={
                               "X-Amz-Target": "secretsmanager.GetSecretValue"},
                           )

    json_data = json.loads(res.data.decode("utf-8"))
    assert json_data['SecretId'] == "test"
