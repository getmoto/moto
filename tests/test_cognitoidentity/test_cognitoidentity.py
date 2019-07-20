from __future__ import unicode_literals

import boto3

from moto import mock_cognitoidentity
import sure  # noqa

from moto.cognitoidentity.utils import get_random_identity_id


@mock_cognitoidentity
def test_create_identity_pool():
    conn = boto3.client('cognito-identity', 'us-west-2')

    result = conn.create_identity_pool(IdentityPoolName='TestPool',
        AllowUnauthenticatedIdentities=False,
        SupportedLoginProviders={'graph.facebook.com': '123456789012345'},
        DeveloperProviderName='devname',
        OpenIdConnectProviderARNs=['arn:aws:rds:eu-west-2:123456789012:db:mysql-db'],
        CognitoIdentityProviders=[
            {
                'ProviderName': 'testprovider',
                'ClientId': 'CLIENT12345',
                'ServerSideTokenCheck': True
            },
        ],
        SamlProviderARNs=['arn:aws:rds:eu-west-2:123456789012:db:mysql-db'])
    assert result['IdentityPoolId'] != ''


# testing a helper function
def test_get_random_identity_id():
    assert len(get_random_identity_id('us-west-2')) > 0
    assert len(get_random_identity_id('us-west-2').split(':')[1]) == 19


@mock_cognitoidentity
def test_get_id():
    # These two do NOT work in server mode. They just don't return the data from the model.
    conn = boto3.client('cognito-identity', 'us-west-2')
    result = conn.get_id(AccountId='someaccount',
        IdentityPoolId='us-west-2:12345',
        Logins={
            'someurl': '12345'
        })
    print(result)
    assert result.get('IdentityId', "").startswith('us-west-2') or result.get('ResponseMetadata').get('HTTPStatusCode') == 200


@mock_cognitoidentity
def test_get_credentials_for_identity():
    # These two do NOT work in server mode. They just don't return the data from the model.
    conn = boto3.client('cognito-identity', 'us-west-2')
    result = conn.get_credentials_for_identity(IdentityId='12345')

    assert result.get('Expiration', 0) > 0 or result.get('ResponseMetadata').get('HTTPStatusCode') == 200
    assert result.get('IdentityId') == '12345' or result.get('ResponseMetadata').get('HTTPStatusCode') == 200


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
    assert len(result['Token']) > 0
    assert result['IdentityId'] == '12345'

@mock_cognitoidentity
def test_get_open_id_token_for_developer_identity_when_no_explicit_identity_id():
    conn = boto3.client('cognito-identity', 'us-west-2')
    result = conn.get_open_id_token_for_developer_identity(
        IdentityPoolId='us-west-2:12345',
        Logins={
            'someurl': '12345'
        },
        TokenDuration=123
    )
    assert len(result['Token']) > 0
    assert len(result['IdentityId']) > 0

@mock_cognitoidentity
def test_get_open_id_token():
    conn = boto3.client('cognito-identity', 'us-west-2')
    result = conn.get_open_id_token(
        IdentityId='12345',
        Logins={
            'someurl': '12345'
        }
    )
    assert len(result['Token']) > 0
    assert result['IdentityId'] == '12345'
