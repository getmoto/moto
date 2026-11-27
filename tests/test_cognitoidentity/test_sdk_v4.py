"""Tests against the AWS SDK for Python v4: https://github.com/aws/aws-sdk-python"""

from uuid import uuid4

import pytest

from moto import mock_aws

try:
    from aws_sdk_cognito_identity import CognitoIdentityClient, CognitoIdentityConfig
    from aws_sdk_cognito_identity.models import ResourceNotFoundException
except ImportError:  # Requires Python 3.12+
    pytest.skip("aws-sdk-cognito-identity is not installed", allow_module_level=True)


@mock_aws
def test_guest_access_for_mobile_app():
    """Give guest users of a mobile app temporary AWS credentials."""
    config = CognitoIdentityConfig.resolve(region="us-east-1")
    pool_name = f"mobile_app_{uuid4().hex}"

    with CognitoIdentityClient(config=config) as client:
        pool = client.create_identity_pool(
            identity_pool_name=pool_name,
            allow_unauthenticated_identities=True,
            developer_provider_name="login.mycompany.myapp",
            identity_pool_tags={"app": "mobile"},
        )
        assert pool.identity_pool_name == pool_name
        assert pool.identity_pool_id.startswith("us-east-1:")
        pool_id = pool.identity_pool_id

        pools = client.list_identity_pools(max_results=60).identity_pools
        assert pool_id in [p.identity_pool_id for p in pools]

        # A guest user opens the app
        identity_id = client.get_id(identity_pool_id=pool_id).identity_id
        assert identity_id.startswith("us-east-1:")

        credentials = client.get_credentials_for_identity(
            identity_id=identity_id
        ).credentials
        assert credentials.access_key_id
        assert credentials.secret_key
        assert credentials.session_token
        assert credentials.expiration is not None

        token = client.get_open_id_token(identity_id=identity_id)
        assert token.identity_id == identity_id
        assert token.token

        identities = client.list_identities(
            identity_pool_id=pool_id, max_results=10
        ).identities
        assert [identity.identity_id for identity in identities] == [identity_id]

        # Guests are no longer welcome
        updated = client.update_identity_pool(
            identity_pool_id=pool_id,
            identity_pool_name=pool_name,
            allow_unauthenticated_identities=False,
        )
        assert updated.allow_unauthenticated_identities is False
        described = client.describe_identity_pool(identity_pool_id=pool_id)
        assert described.allow_unauthenticated_identities is False
        assert described.developer_provider_name == "login.mycompany.myapp"

        client.delete_identity_pool(identity_pool_id=pool_id)
        with pytest.raises(ResourceNotFoundException):
            client.describe_identity_pool(identity_pool_id=pool_id)
