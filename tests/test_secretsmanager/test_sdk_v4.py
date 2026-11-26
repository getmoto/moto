"""Tests against the AWS SDK for Python v4: https://github.com/aws/aws-sdk-python"""

import json
from uuid import uuid4

import pytest

from moto import mock_aws

try:
    from aws_sdk_secrets_manager import SecretsManagerClient, SecretsManagerConfig
    from aws_sdk_secrets_manager.models import InvalidRequestException
except ImportError:  # Requires Python 3.12+
    pytest.skip("aws-sdk-secrets-manager is not installed", allow_module_level=True)


@mock_aws
def test_database_credentials():
    """Store database credentials, rotate the password, and fall back to the previous version."""
    config = SecretsManagerConfig.resolve(region="us-east-1")
    secret_name = f"prod/db/{uuid4()}"

    with SecretsManagerClient(config=config) as client:
        password = client.get_random_password(
            password_length=32, exclude_punctuation=True
        ).random_password
        assert len(password) == 32

        created = client.create_secret(
            name=secret_name,
            description="Credentials for the orders database",
            secret_string=json.dumps({"username": "admin", "password": password}),
            tags=[{"key": "environment", "value": "prod"}],
        )
        assert created.name == secret_name

        current = client.get_secret_value(secret_id=secret_name)
        assert json.loads(current.secret_string)["password"] == password
        assert current.version_stages == ["AWSCURRENT"]

        # Rotate the password
        new_password = client.get_random_password(
            password_length=32, exclude_punctuation=True
        ).random_password
        rotated = client.put_secret_value(
            secret_id=created.arn,
            secret_string=json.dumps({"username": "admin", "password": new_password}),
        )
        assert rotated.version_stages == ["AWSCURRENT"]

        current = client.get_secret_value(secret_id=secret_name)
        assert json.loads(current.secret_string)["password"] == new_password
        previous = client.get_secret_value(
            secret_id=secret_name, version_stage="AWSPREVIOUS"
        )
        assert json.loads(previous.secret_string)["password"] == password

        versions = client.list_secret_version_ids(secret_id=secret_name).versions
        assert {version.version_id for version in versions} == {
            created.version_id,
            rotated.version_id,
        }

        secrets = client.list_secrets(
            filters=[{"key": "name", "values": [secret_name]}]
        ).secret_list
        assert [secret.arn for secret in secrets] == [created.arn]
        assert secrets[0].tags[0].value == "prod"

        deleted = client.delete_secret(secret_id=secret_name, recovery_window_in_days=7)
        assert deleted.deletion_date is not None
        with pytest.raises(InvalidRequestException):
            client.get_secret_value(secret_id=secret_name)

        # Changed our mind - the secret is still needed
        client.restore_secret(secret_id=secret_name)
        description = client.describe_secret(secret_id=secret_name)
        assert description.deleted_date is None
        assert description.description == "Credentials for the orders database"
