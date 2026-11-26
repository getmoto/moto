"""Tests against the AWS SDK for Python v4: https://github.com/aws/aws-sdk-python"""

import io
import json
import zipfile
from uuid import uuid4

import pytest

from moto import mock_aws

try:
    from aws_sdk_iam import IAMClient, IAMConfig
    from aws_sdk_lambda import LambdaClient, LambdaConfig
    from aws_sdk_lambda.models import ResourceNotFoundException
except ImportError:  # Requires Python 3.12+
    pytest.skip(
        "aws-sdk-lambda and aws-sdk-iam are not installed", allow_module_level=True
    )


def _zip_handler() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "lambda_function.py",
            "def lambda_handler(event, context):\n    return event\n",
        )
    return buffer.getvalue()


@mock_aws
def test_deploy_function_with_alias():
    """Deploy a function, reconfigure it, publish a version and point an alias at it."""
    function_name = f"order-processor-{str(uuid4())[:8]}"
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole",
            }
        ],
    }

    with IAMClient(config=IAMConfig.resolve(region="us-east-1")) as iam:
        role = iam.create_role(
            role_name=f"{function_name}-role",
            assume_role_policy_document=json.dumps(trust_policy),
        ).role

    with LambdaClient(config=LambdaConfig.resolve(region="us-east-1")) as client:
        created = client.create_function(
            function_name=function_name,
            runtime="python3.12",
            role=role.arn,
            handler="lambda_function.lambda_handler",
            code={"zip_file": _zip_handler()},
            memory_size=128,
            timeout=10,
            environment={"variables": {"STAGE": "dev"}},
            tags={"team": "orders"},
        )
        assert created.function_name == function_name
        assert created.runtime == "python3.12"
        assert created.role == role.arn
        assert created.environment.variables == {"STAGE": "dev"}

        updated = client.update_function_configuration(
            function_name=function_name,
            memory_size=256,
            environment={"variables": {"STAGE": "prod"}},
        )
        assert updated.memory_size == 256
        assert updated.environment.variables == {"STAGE": "prod"}

        version = client.publish_version(
            function_name=function_name, description="First release"
        )
        assert version.version == "1"

        alias = client.create_alias(
            function_name=function_name, name="live", function_version="1"
        )
        assert alias.alias_arn == f"{created.function_arn}:live"

        versions = client.list_versions_by_function(function_name=function_name)
        assert [v.version for v in versions.versions or []] == ["$LATEST", "1"]

        function = client.get_function(function_name=function_name)
        assert function.configuration.memory_size == 256
        assert function.tags == {"team": "orders"}

        live = client.get_alias(function_name=function_name, name="live")
        assert live.function_version == "1"

        client.delete_function(function_name=function_name)
        with pytest.raises(ResourceNotFoundException):
            client.get_function(function_name=function_name)
