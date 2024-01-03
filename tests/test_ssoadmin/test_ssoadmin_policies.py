import json

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_ssoadmin

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html

DUMMY_PERMISSIONSET_ID = (
    "arn:aws:sso:::permissionSet/ins-eeeeffffgggghhhh/ps-hhhhkkkkppppoooo"
)
DUMMY_INSTANCE_ARN = "arn:aws:sso:::instance/ins-aaaabbbbccccdddd"


def create_permissionset(client) -> str:
    """Helper function to create a dummy permission set and returns the arn."""

    response = client.create_permission_set(
        Name="test-permission-set",
        InstanceArn=DUMMY_INSTANCE_ARN,
        Description="test permission set",
    )

    return response["PermissionSet"]["PermissionSetArn"]


@mock_ssoadmin
def test_put_inline_policy_to_permission_set():
    """
    Tests putting and getting an inline policy to a permission set.
    """
    client = boto3.client("sso-admin", region_name="us-east-1")

    permission_set_arn = create_permissionset(client)
    dummy_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "s3:GetObject",
                "Resource": "arn:aws:s3:::your-bucket-name/*",
            }
        ],
    }

    # Happy path
    response = client.put_inline_policy_to_permission_set(
        InstanceArn=DUMMY_INSTANCE_ARN,
        PermissionSetArn=permission_set_arn,
        InlinePolicy=json.dumps(dummy_policy),
    )

    response = client.get_inline_policy_for_permission_set(
        InstanceArn=DUMMY_INSTANCE_ARN,
        PermissionSetArn=permission_set_arn,
    )

    assert response["InlinePolicy"] == json.dumps(dummy_policy)

    # Invalid permission set arn
    not_create_ps_arn = (
        "arn:aws:sso:::permissionSet/ins-eeeeffffgggghhhh/ps-hhhhkkkkppppoxyz"
    )
    with pytest.raises(ClientError) as e:
        client.put_inline_policy_to_permission_set(
            InstanceArn=DUMMY_INSTANCE_ARN,
            PermissionSetArn=not_create_ps_arn,
            InlinePolicy=json.dumps(dummy_policy),
        )
    err = e.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "Could not find PermissionSet with id ps-hhhhkkkkppppoxyz"


@mock_ssoadmin
def test_get_inline_policy_to_permission_set_no_policy():
    client = boto3.client("sso-admin", region_name="us-east-1")

    permission_set_arn = create_permissionset(client)

    response = client.get_inline_policy_for_permission_set(
        InstanceArn=DUMMY_INSTANCE_ARN,
        PermissionSetArn=permission_set_arn,
    )

    assert response["InlinePolicy"] == ""


@mock_ssoadmin
def test_delete_inline_policy_to_permissionset():
    client = boto3.client("sso-admin", region_name="us-east-1")

    permission_set_arn = create_permissionset(client)

    dummy_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "s3:GetObject",
                "Resource": "arn:aws:s3:::your-bucket-name/*",
            }
        ],
    }

    client.put_inline_policy_to_permission_set(
        InstanceArn=DUMMY_INSTANCE_ARN,
        PermissionSetArn=permission_set_arn,
        InlinePolicy=json.dumps(dummy_policy),
    )

    response = client.get_inline_policy_for_permission_set(
        InstanceArn=DUMMY_INSTANCE_ARN,
        PermissionSetArn=permission_set_arn,
    )

    assert response["InlinePolicy"] == json.dumps(dummy_policy)

    client.delete_inline_policy_from_permission_set(
        InstanceArn=DUMMY_INSTANCE_ARN,
        PermissionSetArn=permission_set_arn,
    )

    response = client.get_inline_policy_for_permission_set(
        InstanceArn=DUMMY_INSTANCE_ARN,
        PermissionSetArn=permission_set_arn,
    )

    assert response["InlinePolicy"] == ""
