from __future__ import unicode_literals

import base64
import botocore.client
import boto3
import hashlib
import io
import json
import zipfile
import sure  # noqa

from freezegun import freeze_time
from moto import mock_cognitoidentity, settings

@mock_cognitoidentity
def test_create_identity_pool():
    conn = boto3.client('cognito-identity', 'us-west-2')

    result = conn.create_identity_pool(IdentityPoolName='TestPool',
        AllowUnauthenticatedIdentities=False,          
        SupportedLoginProviders={'graph.facebook.com':'123456789012345'},
        DeveloperProviderName='devname',
        OpenIdConnectProviderARNs=['arn:aws:rds:eu-west-2:123456789012:db:mysql-db',],
        CognitoIdentityProviders=[
            {
                'ProviderName': 'testprovider',
                'ClientId': 'CLIENT12345',
                'ServerSideTokenCheck': True
            },
        ],
        SamlProviderARNs=['arn:aws:rds:eu-west-2:123456789012:db:mysql-db',])
    assert result['IdentityPoolId'] != ''

@mock_cognitoidentity
def test_get_id():
    conn = boto3.client('cognito-identity', 'us-west-2')
    result = conn.get_id(AccountId='someaccount',
        IdentityPoolId='us-west-2:12345',
        Logins={
                'someurl': '12345'
        })
    assert result['IdentityId'].startswith('us-west-2')

@mock_cognitoidentity
def test_get_credentials_for_identity():
    conn = boto3.client('cognito-identity', 'us-west-2')
    result = conn.get_credentials_for_identity(IdentityId='12345')
    assert result['IdentityId'] == '12345'

@mock_cognitoidentity
def test_get_open_id_token_for_developer_identity():
    conn = boto3.client('cognito-identity', 'us-west-2')
    result = conn.get_open_id_token_for_developer_identity(
        IdentityPoolId='us-west-2:12345',
        IdentityId='12345',
        Logins={
            'someurl': '12345'
        },
        TokenDuration=123
    )
    assert result['IdentityId'] == '12345'
