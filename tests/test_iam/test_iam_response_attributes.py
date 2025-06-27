import json
from typing import Any
from uuid import uuid4

import boto3
import pytest
from botocore.exceptions import ClientError

from tests import aws_verified

BOUNDARY_POLICY = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "BoundaryAllowAllNotAdminAccess",
            "Effect": "Allow",
            "Action": "*",
            "Resource": "*",
            "Condition": {
                "ArnNotEquals": {
                    "iam:PolicyArn": ["arn:aws:iam::aws:policy/AdministratorAccess"]
                }
            },
        }
    ],
}

DEFAULT_TAGS = [{"Key": "somekey", "Value": "somevalue"}]


@aws_verified
@pytest.mark.aws_verified
@pytest.mark.parametrize(
    "specify_optional_params",
    [True, False],
    ids=("SpecifyOptionalParams", "NoOptionalParams"),
)
def test_role_resource_returns_subset_of_available_attributes(specify_optional_params):
    client = boto3.client("iam", region_name="us-east-1")
    role_policy = {
        "Version": "2012-10-17",
        "Statement": {
            "Effect": "Allow",
            "Principal": {"Service": "ec2.amazonaws.com"},
            "Action": "sts:AssumeRole",
        },
    }
    test_guid = str(uuid4())
    role_name = "TestRole" + test_guid
    boundary_policy_name = "TestBoundaryPolicy" + test_guid
    resp = client.create_policy(
        PolicyName=boundary_policy_name, PolicyDocument=json.dumps(BOUNDARY_POLICY)
    )
    boundary_policy_arn = resp["Policy"]["Arn"]
    try:
        path = f"/{test_guid}/"
        create_role_params: dict[str, Any] = dict(
            Path=path,
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(role_policy),
            Description="test",
        )
        if specify_optional_params:
            create_role_params["PermissionsBoundary"] = boundary_policy_arn
            create_role_params["Tags"] = DEFAULT_TAGS

        def assert_resource_attributes(resource):
            permissions_boundary_in_response = "PermissionsBoundary" in resource
            assert permissions_boundary_in_response is bool(specify_optional_params), (
                f"PermissionsBoundary in response: {permissions_boundary_in_response}, "
                f"but specify_optional_params is {specify_optional_params}"
            )
            tags_in_response = "Tags" in resource
            assert tags_in_response is bool(specify_optional_params), (
                f"Tags in response: {tags_in_response}, "
                f"but specify_optional_params is {specify_optional_params}"
            )

        # Create/GetRole calls return some attributes only when specified.
        resp = client.create_role(**create_role_params)
        assert_resource_attributes(resp["Role"])
        resp = client.get_role(RoleName=role_name)
        assert_resource_attributes(resp["Role"])
        # ListRoles always returns a subset of all available attributes.
        resp = client.list_roles(PathPrefix=path)
        assert len(resp["Roles"]) == 1
        role = resp["Roles"][0]
        assert "PermissionsBoundary" not in role
        assert "RoleLastUsed" not in role
        assert "Tags" not in role
    finally:
        # Clean up created AWS resources
        try:
            client.delete_role(RoleName=role_name)
        except ClientError as e:
            if e.response["Error"]["Code"] != "NoSuchEntity":
                raise
        try:
            client.delete_policy(PolicyArn=boundary_policy_arn)
        except ClientError as e:
            if e.response["Error"]["Code"] != "NoSuchEntity":
                raise


@aws_verified
@pytest.mark.aws_verified
@pytest.mark.parametrize(
    "specify_optional_params",
    [True, False],
    ids=("SpecifyOptionalParams", "NoOptionalParams"),
)
def test_user_resource_returns_subset_of_available_attributes(specify_optional_params):
    client = boto3.client("iam", region_name="us-east-1")
    test_guid = str(uuid4())
    user_name = "TestUser" + test_guid
    boundary_policy_name = "TestBoundaryPolicy" + test_guid
    resp = client.create_policy(
        PolicyName=boundary_policy_name, PolicyDocument=json.dumps(BOUNDARY_POLICY)
    )
    boundary_policy_arn = resp["Policy"]["Arn"]
    try:
        path = f"/{test_guid}/"
        create_user_params: dict[str, Any] = dict(
            Path=path,
            UserName=user_name,
        )
        if specify_optional_params:
            create_user_params["PermissionsBoundary"] = boundary_policy_arn
            create_user_params["Tags"] = DEFAULT_TAGS

        def assert_resource_attributes(resource):
            # TODO: Uncomment this when moto supports PermissionsBoundary for Users
            # permissions_boundary_in_response = "PermissionsBoundary" in resource
            # assert permissions_boundary_in_response is bool(specify_optional_params), (
            #     f"PermissionsBoundary in response: {permissions_boundary_in_response}, "
            #     f"but specify_optional_params is {specify_optional_params}"
            # )
            tags_in_response = "Tags" in resource
            assert tags_in_response is bool(specify_optional_params), (
                f"Tags in response: {tags_in_response}, "
                f"but specify_optional_params is {specify_optional_params}"
            )

        # Create/GetUser calls return some attributes only when specified.
        resp = client.create_user(**create_user_params)
        assert_resource_attributes(resp["User"])
        resp = client.get_user(UserName=user_name)
        assert_resource_attributes(resp["User"])
        # ListUsers always returns a subset of all available attributes.
        resp = client.list_users(PathPrefix=path)
        assert len(resp["Users"]) == 1
        user = resp["Users"][0]
        assert "PermissionsBoundary" not in user
        assert "Tags" not in user
    finally:
        # Clean up created AWS resources
        try:
            client.delete_user(UserName=user_name)
        except ClientError as e:
            if e.response["Error"]["Code"] != "NoSuchEntity":
                raise
        try:
            client.delete_policy(PolicyArn=boundary_policy_arn)
        except ClientError as e:
            if e.response["Error"]["Code"] != "NoSuchEntity":
                raise


@aws_verified
@pytest.mark.aws_verified
@pytest.mark.parametrize(
    "specify_optional_params",
    [True, False],
    ids=("SpecifyOptionalParams", "NoOptionalParams"),
)
def test_policy_resource_returns_subset_of_available_attributes(
    specify_optional_params,
):
    client = boto3.client("iam", region_name="us-east-1")
    test_guid = str(uuid4())
    policy_arn = None
    try:
        policy_name = "TestPolicy" + test_guid
        path = f"/{test_guid}/"
        create_policy_params: dict[str, Any] = dict(
            Path=path,
            PolicyName=policy_name,
            PolicyDocument=json.dumps(BOUNDARY_POLICY),
        )
        if specify_optional_params:
            create_policy_params["Description"] = "test description"
            create_policy_params["Tags"] = DEFAULT_TAGS

        # CreatePolicy returns some attributes only when specified.
        resp = client.create_policy(**create_policy_params)
        policy_arn = resp["Policy"]["Arn"]
        assert "Description" not in resp["Policy"]
        tags_in_response = "Tags" in resp["Policy"]
        assert tags_in_response is bool(specify_optional_params), (
            f"Tags in response: {tags_in_response}, "
            f"but specify_optional_params is {specify_optional_params}"
        )
        # GetPolicy *does* return empty tags list...
        resp = client.get_policy(PolicyArn=policy_arn)
        description_in_response = "Description" in resp["Policy"]
        assert description_in_response is bool(specify_optional_params), (
            f"Description in response: {description_in_response}, "
            f"but specify_optional_params is {specify_optional_params}"
        )
        assert "Tags" in resp["Policy"]
        # ListPolices always returns a subset of all available attributes.
        resp = client.list_policies(PathPrefix=path)
        assert len(resp["Policies"]) == 1
        policy = resp["Policies"][0]
        assert "Description" not in policy
        assert "Tags" not in policy
    finally:
        # Clean up created AWS resources
        try:
            if policy_arn is not None:
                client.delete_policy(PolicyArn=policy_arn)
        except ClientError as e:
            if e.response["Error"]["Code"] != "NoSuchEntity":
                raise
