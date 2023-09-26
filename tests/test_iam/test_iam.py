import json

import boto3
import csv
from botocore.exceptions import ClientError

from moto import mock_config, mock_iam, settings
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from moto.core.utils import utcnow
from moto.iam import iam_backends
from moto.backends import get_backend
from tests import DEFAULT_ACCOUNT_ID
import pytest

from datetime import datetime
from uuid import uuid4
from urllib import parse

from moto.s3.responses import DEFAULT_REGION_NAME


MOCK_CERT = """-----BEGIN CERTIFICATE-----
MIIBpzCCARACCQCY5yOdxCTrGjANBgkqhkiG9w0BAQsFADAXMRUwEwYDVQQKDAxt
b3RvIHRlc3RpbmcwIBcNMTgxMTA1MTkwNTIwWhgPMjI5MjA4MTkxOTA1MjBaMBcx
FTATBgNVBAoMDG1vdG8gdGVzdGluZzCBnzANBgkqhkiG9w0BAQEFAAOBjQAwgYkC
gYEA1Jn3g2h7LD3FLqdpcYNbFXCS4V4eDpuTCje9vKFcC3pi/01147X3zdfPy8Mt
ZhKxcREOwm4NXykh23P9KW7fBovpNwnbYsbPqj8Hf1ZaClrgku1arTVhEnKjx8zO
vaR/bVLCss4uE0E0VM1tJn/QGQsfthFsjuHtwx8uIWz35tUCAwEAATANBgkqhkiG
9w0BAQsFAAOBgQBWdOQ7bDc2nWkUhFjZoNIZrqjyNdjlMUndpwREVD7FQ/DuxJMj
FyDHrtlrS80dPUQWNYHw++oACDpWO01LGLPPrGmuO/7cOdojPEd852q5gd+7W9xt
8vUH+pBa6IBLbvBp+szli51V3TLSWcoyy4ceJNQU2vCkTLoFdS0RLd/7tQ==
-----END CERTIFICATE-----"""

MOCK_POLICY = """
{
  "Version": "2012-10-17",
  "Statement":
    {
      "Effect": "Allow",
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::example_bucket"
    }
}
"""

MOCK_POLICY_2 = """
{
  "Version": "2012-10-17",
  "Id": "2",
  "Statement":
    {
      "Effect": "Allow",
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::example_bucket"
    }
}
"""

MOCK_POLICY_3 = """
{
  "Version": "2012-10-17",
  "Id": "3",
  "Statement":
    {
      "Effect": "Allow",
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::example_bucket"
    }
}
"""

MOCK_STS_EC2_POLICY_DOCUMENT = """{
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Principal": {
            "Service": [
              "ec2.amazonaws.com"
            ]
          },
          "Action": [
            "sts:AssumeRole"
          ]
        }
      ]
    }"""


@mock_iam
def test_get_role__should_throw__when_role_does_not_exist():
    conn = boto3.client("iam", region_name="us-east-1")
    with pytest.raises(ClientError) as ex:
        conn.get_role(RoleName="unexisting_role")
    err = ex.value.response["Error"]
    assert err["Code"] == "NoSuchEntity"
    assert "not found" in err["Message"]


@mock_iam
def test_get_role__should_contain_last_used():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_role(
        RoleName="my-role", AssumeRolePolicyDocument="some policy", Path="/"
    )
    role = conn.get_role(RoleName="my-role")["Role"]
    assert role["RoleLastUsed"] == {}

    if not settings.TEST_SERVER_MODE:
        iam_backend = get_backend("iam")[ACCOUNT_ID]["global"]
        last_used = datetime.strptime(
            "2022-07-18T10:30:00+00:00", "%Y-%m-%dT%H:%M:%S+00:00"
        )
        region = "us-west-1"
        iam_backend.roles[role["RoleId"]].last_used = last_used
        iam_backend.roles[role["RoleId"]].last_used_region = region
        roleLastUsed = conn.get_role(RoleName="my-role")["Role"]["RoleLastUsed"]
        assert roleLastUsed["LastUsedDate"].replace(tzinfo=None) == last_used
        assert roleLastUsed["Region"] == region


@mock_iam
def test_get_instance_profile__should_throw__when_instance_profile_does_not_exist():
    conn = boto3.client("iam", region_name="us-east-1")
    with pytest.raises(ClientError) as ex:
        conn.get_instance_profile(InstanceProfileName="unexisting_instance_profile")
    err = ex.value.response["Error"]
    assert err["Code"] == "NoSuchEntity"
    assert "not found" in err["Message"]


@mock_iam
def test_create_role_and_instance_profile():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_instance_profile(InstanceProfileName="my-profile", Path="my-path")
    conn.create_role(
        RoleName="my-role", AssumeRolePolicyDocument="some policy", Path="/my-path/"
    )

    conn.add_role_to_instance_profile(
        InstanceProfileName="my-profile", RoleName="my-role"
    )

    role = conn.get_role(RoleName="my-role")["Role"]
    assert role["Path"] == "/my-path/"
    assert role["AssumeRolePolicyDocument"] == "some policy"

    profile = conn.get_instance_profile(InstanceProfileName="my-profile")[
        "InstanceProfile"
    ]
    assert profile["Path"] == "my-path"

    assert len(profile["Roles"]) == 1
    role_from_profile = profile["Roles"][0]
    assert role_from_profile["RoleId"] == role["RoleId"]
    assert role_from_profile["RoleName"] == "my-role"

    assert conn.list_roles()["Roles"][0]["RoleName"] == "my-role"

    # Test with an empty path:
    profile = conn.create_instance_profile(InstanceProfileName="my-other-profile")
    assert profile["InstanceProfile"]["Path"] == "/"


@mock_iam
def test_create_instance_profile_should_throw_when_name_is_not_unique():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_instance_profile(InstanceProfileName="unique-instance-profile")
    with pytest.raises(ClientError):
        conn.create_instance_profile(InstanceProfileName="unique-instance-profile")


@mock_iam
def test_create_add_additional_roles_to_instance_profile_error():

    # Setup
    iam = boto3.client("iam", region_name="us-east-1")
    name = "test_profile"
    role_name = "test_role"
    role_name2 = "test_role2"
    iam.create_instance_profile(InstanceProfileName=name)
    iam.create_role(
        RoleName=role_name, AssumeRolePolicyDocument=MOCK_STS_EC2_POLICY_DOCUMENT
    )
    iam.create_role(
        RoleName=role_name2, AssumeRolePolicyDocument=MOCK_STS_EC2_POLICY_DOCUMENT
    )
    iam.add_role_to_instance_profile(InstanceProfileName=name, RoleName=role_name)

    # Execute
    with pytest.raises(ClientError) as exc:
        iam.add_role_to_instance_profile(InstanceProfileName=name, RoleName=role_name2)

    # Verify
    err = exc.value.response["Error"]
    assert err["Code"] == "LimitExceeded"
    assert (
        err["Message"]
        == "Cannot exceed quota for InstanceSessionsPerInstanceProfile: 1"
    )


@mock_iam
def test_remove_role_from_instance_profile():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_instance_profile(InstanceProfileName="my-profile", Path="my-path")
    conn.create_role(
        RoleName="my-role", AssumeRolePolicyDocument="some policy", Path="/my-path/"
    )
    conn.add_role_to_instance_profile(
        InstanceProfileName="my-profile", RoleName="my-role"
    )

    profile = conn.get_instance_profile(InstanceProfileName="my-profile")[
        "InstanceProfile"
    ]
    assert len(profile["Roles"]) == 1

    conn.remove_role_from_instance_profile(
        InstanceProfileName="my-profile", RoleName="my-role"
    )

    profile = conn.get_instance_profile(InstanceProfileName="my-profile")[
        "InstanceProfile"
    ]
    assert len(profile["Roles"]) == 0


@mock_iam()
def test_delete_instance_profile():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_role(
        RoleName="my-role", AssumeRolePolicyDocument="some policy", Path="/my-path/"
    )
    conn.create_instance_profile(InstanceProfileName="my-profile")
    conn.add_role_to_instance_profile(
        InstanceProfileName="my-profile", RoleName="my-role"
    )
    with pytest.raises(conn.exceptions.DeleteConflictException):
        conn.delete_instance_profile(InstanceProfileName="my-profile")
    conn.remove_role_from_instance_profile(
        InstanceProfileName="my-profile", RoleName="my-role"
    )
    conn.delete_instance_profile(InstanceProfileName="my-profile")
    with pytest.raises(conn.exceptions.NoSuchEntityException):
        conn.get_instance_profile(InstanceProfileName="my-profile")


@mock_iam()
def test_get_login_profile():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_user(UserName="my-user")
    conn.create_login_profile(UserName="my-user", Password="my-pass")

    response = conn.get_login_profile(UserName="my-user")
    assert response["LoginProfile"]["UserName"] == "my-user"


@mock_iam()
def test_update_login_profile():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_user(UserName="my-user")
    conn.create_login_profile(UserName="my-user", Password="my-pass")
    response = conn.get_login_profile(UserName="my-user")
    assert response["LoginProfile"].get("PasswordResetRequired") is None

    conn.update_login_profile(
        UserName="my-user", Password="new-pass", PasswordResetRequired=True
    )
    response = conn.get_login_profile(UserName="my-user")
    assert response["LoginProfile"].get("PasswordResetRequired") is True


@mock_iam()
def test_delete_role():
    conn = boto3.client("iam", region_name="us-east-1")

    with pytest.raises(conn.exceptions.NoSuchEntityException):
        conn.delete_role(RoleName="my-role")

    # Test deletion failure with a managed policy
    conn.create_role(
        RoleName="my-role", AssumeRolePolicyDocument="some policy", Path="/my-path/"
    )
    response = conn.create_policy(
        PolicyName="my-managed-policy", PolicyDocument=MOCK_POLICY
    )
    conn.attach_role_policy(PolicyArn=response["Policy"]["Arn"], RoleName="my-role")
    with pytest.raises(conn.exceptions.DeleteConflictException):
        conn.delete_role(RoleName="my-role")
    conn.detach_role_policy(PolicyArn=response["Policy"]["Arn"], RoleName="my-role")
    conn.delete_policy(PolicyArn=response["Policy"]["Arn"])
    conn.delete_role(RoleName="my-role")
    with pytest.raises(conn.exceptions.NoSuchEntityException):
        conn.get_role(RoleName="my-role")

    # Test deletion failure with an inline policy
    conn.create_role(
        RoleName="my-role", AssumeRolePolicyDocument="some policy", Path="/my-path/"
    )
    conn.put_role_policy(
        RoleName="my-role", PolicyName="my-role-policy", PolicyDocument=MOCK_POLICY
    )
    with pytest.raises(conn.exceptions.DeleteConflictException):
        conn.delete_role(RoleName="my-role")
    conn.delete_role_policy(RoleName="my-role", PolicyName="my-role-policy")
    conn.delete_role(RoleName="my-role")
    with pytest.raises(conn.exceptions.NoSuchEntityException):
        conn.get_role(RoleName="my-role")

    # Test deletion failure with attachment to an instance profile
    conn.create_role(
        RoleName="my-role", AssumeRolePolicyDocument="some policy", Path="/my-path/"
    )
    conn.create_instance_profile(InstanceProfileName="my-profile")
    conn.add_role_to_instance_profile(
        InstanceProfileName="my-profile", RoleName="my-role"
    )
    with pytest.raises(conn.exceptions.DeleteConflictException):
        conn.delete_role(RoleName="my-role")
    conn.remove_role_from_instance_profile(
        InstanceProfileName="my-profile", RoleName="my-role"
    )
    conn.delete_role(RoleName="my-role")
    with pytest.raises(conn.exceptions.NoSuchEntityException):
        conn.get_role(RoleName="my-role")

    # Test deletion with no conflicts
    conn.create_role(
        RoleName="my-role", AssumeRolePolicyDocument="some policy", Path="/my-path/"
    )
    conn.delete_role(RoleName="my-role")
    with pytest.raises(conn.exceptions.NoSuchEntityException):
        conn.get_role(RoleName="my-role")


@mock_iam
def test_list_instance_profiles():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_instance_profile(InstanceProfileName="my-profile", Path="my-path")
    conn.create_role(
        RoleName="my-role", AssumeRolePolicyDocument="some policy", Path="/my-path/"
    )

    conn.add_role_to_instance_profile(
        InstanceProfileName="my-profile", RoleName="my-role"
    )

    profiles = conn.list_instance_profiles()["InstanceProfiles"]

    assert len(profiles) == 1
    assert profiles[0]["InstanceProfileName"] == "my-profile"
    assert profiles[0]["Roles"][0]["RoleName"] == "my-role"


@mock_iam
def test_list_instance_profiles_for_role():
    conn = boto3.client("iam", region_name="us-east-1")

    conn.create_role(
        RoleName="my-role", AssumeRolePolicyDocument="some policy", Path="my-path"
    )
    conn.create_role(
        RoleName="my-role2", AssumeRolePolicyDocument="some policy2", Path="my-path2"
    )

    profile_name_list = ["my-profile", "my-profile2"]
    profile_path_list = ["my-path", "my-path2"]
    for profile_count in range(0, 2):
        conn.create_instance_profile(
            InstanceProfileName=profile_name_list[profile_count],
            Path=profile_path_list[profile_count],
        )

    for profile_count in range(0, 2):
        conn.add_role_to_instance_profile(
            InstanceProfileName=profile_name_list[profile_count], RoleName="my-role"
        )

    profile_dump = conn.list_instance_profiles_for_role(RoleName="my-role")
    profile_list = profile_dump["InstanceProfiles"]
    for profile_count in range(0, len(profile_list)):
        profile_name_list.remove(profile_list[profile_count]["InstanceProfileName"])
        profile_path_list.remove(profile_list[profile_count]["Path"])
        assert profile_list[profile_count]["Roles"][0]["RoleName"] == "my-role"

    assert len(profile_name_list) == 0
    assert len(profile_path_list) == 0

    profile_dump2 = conn.list_instance_profiles_for_role(RoleName="my-role2")
    profile_list = profile_dump2["InstanceProfiles"]
    assert len(profile_list) == 0


@mock_iam
def test_list_role_policies():
    conn = boto3.client("iam", region_name="us-east-1")

    conn.create_role(
        RoleName="my-role", AssumeRolePolicyDocument="some policy", Path="my-path"
    )
    conn.put_role_policy(
        RoleName="my-role", PolicyName="test policy", PolicyDocument=MOCK_POLICY
    )
    role = conn.list_role_policies(RoleName="my-role")
    assert role["PolicyNames"] == ["test policy"]

    conn.put_role_policy(
        RoleName="my-role", PolicyName="test policy 2", PolicyDocument=MOCK_POLICY
    )
    role = conn.list_role_policies(RoleName="my-role")
    assert len(role["PolicyNames"]) == 2

    conn.delete_role_policy(RoleName="my-role", PolicyName="test policy")
    role = conn.list_role_policies(RoleName="my-role")
    assert role["PolicyNames"] == ["test policy 2"]

    with pytest.raises(ClientError) as ex:
        conn.delete_role_policy(RoleName="my-role", PolicyName="test policy")
    err = ex.value.response["Error"]
    assert err["Code"] == "NoSuchEntity"
    assert err["Message"] == "The role policy with name test policy cannot be found."


@mock_iam
def test_put_role_policy():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_role(
        RoleName="my-role", AssumeRolePolicyDocument="some policy", Path="my-path"
    )
    conn.put_role_policy(
        RoleName="my-role", PolicyName="test policy", PolicyDocument=MOCK_POLICY
    )
    policy = conn.get_role_policy(RoleName="my-role", PolicyName="test policy")
    assert policy["PolicyName"] == "test policy"
    assert policy["PolicyDocument"] == json.loads(MOCK_POLICY)


@mock_iam
def test_get_role_policy():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_role(
        RoleName="my-role", AssumeRolePolicyDocument="some policy", Path="my-path"
    )
    with pytest.raises(conn.exceptions.NoSuchEntityException):
        conn.get_role_policy(RoleName="my-role", PolicyName="does-not-exist")


@mock_iam
def test_update_assume_role_invalid_policy():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_role(
        RoleName="my-role", AssumeRolePolicyDocument="some policy", Path="my-path"
    )
    with pytest.raises(ClientError) as ex:
        conn.update_assume_role_policy(RoleName="my-role", PolicyDocument="new policy")
    err = ex.value.response["Error"]
    assert err["Code"] == "MalformedPolicyDocument"
    assert "Syntax errors in policy." in err["Message"]


@mock_iam
def test_update_assume_role_valid_policy():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_role(
        RoleName="my-role", AssumeRolePolicyDocument="some policy", Path="my-path"
    )
    policy_document = MOCK_STS_EC2_POLICY_DOCUMENT
    conn.update_assume_role_policy(RoleName="my-role", PolicyDocument=policy_document)
    role = conn.get_role(RoleName="my-role")["Role"]
    assert (
        role["AssumeRolePolicyDocument"]["Statement"][0]["Action"][0]
        == "sts:AssumeRole"
    )


@mock_iam
def test_update_assume_role_invalid_policy_bad_action():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_role(
        RoleName="my-role", AssumeRolePolicyDocument="some policy", Path="my-path"
    )
    policy_document = """
    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": ["ec2.amazonaws.com"]
                },
                "Action": ["sts:BadAssumeRole"]
            }
        ]
    }
"""

    with pytest.raises(ClientError) as ex:
        conn.update_assume_role_policy(
            RoleName="my-role", PolicyDocument=policy_document
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "MalformedPolicyDocument"
    assert (
        "Trust Policy statement actions can only be sts:AssumeRole, sts:AssumeRoleWithSAML,  and sts:AssumeRoleWithWebIdentity"
        in err["Message"]
    )


@mock_iam
def test_update_assume_role_invalid_policy_with_resource():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_role(
        RoleName="my-role", AssumeRolePolicyDocument="some policy", Path="my-path"
    )
    policy_document = """
    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": ["ec2.amazonaws.com"]
                },
                "Action": ["sts:AssumeRole"],
                "Resource" : "arn:aws:s3:::example_bucket"
            }
        ]
    }
    """

    with pytest.raises(ClientError) as ex:
        conn.update_assume_role_policy(
            RoleName="my-role", PolicyDocument=policy_document
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "MalformedPolicyDocument"
    assert "Has prohibited field Resource." in err["Message"]


@mock_iam
def test_create_policy():
    conn = boto3.client("iam", region_name="us-east-1")
    response = conn.create_policy(
        PolicyName="TestCreatePolicy", PolicyDocument=MOCK_POLICY
    )
    assert (
        response["Policy"]["Arn"]
        == f"arn:aws:iam::{ACCOUNT_ID}:policy/TestCreatePolicy"
    )


@mock_iam
def test_create_policy_already_exists():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_policy(PolicyName="TestCreatePolicy", PolicyDocument=MOCK_POLICY)
    with pytest.raises(conn.exceptions.EntityAlreadyExistsException) as ex:
        conn.create_policy(PolicyName="TestCreatePolicy", PolicyDocument=MOCK_POLICY)
    assert ex.value.response["Error"]["Code"] == "EntityAlreadyExists"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 409
    assert "TestCreatePolicy" in ex.value.response["Error"]["Message"]


@mock_iam
def test_delete_policy():
    conn = boto3.client("iam", region_name="us-east-1")
    response = conn.create_policy(
        PolicyName="TestCreatePolicy", PolicyDocument=MOCK_POLICY
    )
    assert [
        pol["PolicyName"] for pol in conn.list_policies(Scope="Local")["Policies"]
    ] == ["TestCreatePolicy"]
    conn.delete_policy(PolicyArn=response["Policy"]["Arn"])
    assert conn.list_policies(Scope="Local")["Policies"] == []


@mock_iam
def test_create_policy_versions():
    conn = boto3.client("iam", region_name="us-east-1")
    with pytest.raises(ClientError):
        conn.create_policy_version(
            PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestCreatePolicyVersion",
            PolicyDocument='{"some":"policy"}',
        )
    conn.create_policy(PolicyName="TestCreatePolicyVersion", PolicyDocument=MOCK_POLICY)
    version = conn.create_policy_version(
        PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestCreatePolicyVersion",
        PolicyDocument=MOCK_POLICY,
        SetAsDefault=True,
    )
    assert version.get("PolicyVersion")["Document"] == json.loads(MOCK_POLICY)
    assert version.get("PolicyVersion")["VersionId"] == "v2"
    assert version.get("PolicyVersion")["IsDefaultVersion"] is True
    conn.delete_policy_version(
        PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestCreatePolicyVersion",
        VersionId="v1",
    )
    version = conn.create_policy_version(
        PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestCreatePolicyVersion",
        PolicyDocument=MOCK_POLICY,
    )
    assert version.get("PolicyVersion")["VersionId"] == "v3"
    assert version.get("PolicyVersion")["IsDefaultVersion"] is False


@mock_iam
def test_create_many_policy_versions():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_policy(
        PolicyName="TestCreateManyPolicyVersions", PolicyDocument=MOCK_POLICY
    )
    for _ in range(0, 4):
        conn.create_policy_version(
            PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestCreateManyPolicyVersions",
            PolicyDocument=MOCK_POLICY,
        )
    with pytest.raises(ClientError):
        conn.create_policy_version(
            PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestCreateManyPolicyVersions",
            PolicyDocument=MOCK_POLICY,
        )


@mock_iam
def test_set_default_policy_version():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_policy(
        PolicyName="TestSetDefaultPolicyVersion", PolicyDocument=MOCK_POLICY
    )
    conn.create_policy_version(
        PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestSetDefaultPolicyVersion",
        PolicyDocument=MOCK_POLICY_2,
        SetAsDefault=True,
    )
    conn.create_policy_version(
        PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestSetDefaultPolicyVersion",
        PolicyDocument=MOCK_POLICY_3,
        SetAsDefault=True,
    )
    versions = conn.list_policy_versions(
        PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestSetDefaultPolicyVersion"
    )
    assert versions["Versions"][0]["Document"] == json.loads(MOCK_POLICY)
    assert versions["Versions"][0]["IsDefaultVersion"] is False
    assert versions["Versions"][1]["Document"] == json.loads(MOCK_POLICY_2)
    assert versions["Versions"][1]["IsDefaultVersion"] is False
    assert versions["Versions"][2]["Document"] == json.loads(MOCK_POLICY_3)
    assert versions["Versions"][2]["IsDefaultVersion"] is True

    conn.set_default_policy_version(
        PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestSetDefaultPolicyVersion",
        VersionId="v1",
    )
    versions = conn.list_policy_versions(
        PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestSetDefaultPolicyVersion"
    )
    assert versions["Versions"][0]["Document"] == json.loads(MOCK_POLICY)
    assert versions["Versions"][0]["IsDefaultVersion"] is True
    assert versions["Versions"][1]["Document"] == json.loads(MOCK_POLICY_2)
    assert versions["Versions"][1]["IsDefaultVersion"] is False
    assert versions["Versions"][2]["Document"] == json.loads(MOCK_POLICY_3)
    assert versions["Versions"][2]["IsDefaultVersion"] is False

    # Set default version for non-existing policy
    with pytest.raises(ClientError) as exc:
        conn.set_default_policy_version(
            PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestNonExistingPolicy",
            VersionId="v1",
        )
    err = exc.value.response["Error"]
    assert (
        err["Message"]
        == f"Policy arn:aws:iam::{ACCOUNT_ID}:policy/TestNonExistingPolicy not found"
    )

    # Set default version for incorrect version
    with pytest.raises(ClientError) as exc:
        conn.set_default_policy_version(
            PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestSetDefaultPolicyVersion",
            VersionId="wrong_version_id",
        )
    err = exc.value.response["Error"]
    assert (
        err["Message"]
        == r"Value 'wrong_version_id' at 'versionId' failed to satisfy constraint: Member must satisfy regular expression pattern: v[1-9][0-9]*(\.[A-Za-z0-9-]*)?"
    )

    # Set default version for non-existing version
    with pytest.raises(ClientError) as exc:
        conn.set_default_policy_version(
            PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestSetDefaultPolicyVersion",
            VersionId="v4",
        )
    err = exc.value.response["Error"]
    assert (
        err["Message"]
        == f"Policy arn:aws:iam::{ACCOUNT_ID}:policy/TestSetDefaultPolicyVersion version v4 does not exist or is not attachable."
    )


@mock_iam
def test_get_policy():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_policy(PolicyName="TestGetPolicy", PolicyDocument=MOCK_POLICY)
    policy = conn.get_policy(
        PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestGetPolicy"
    )
    assert policy["Policy"]["Arn"] == f"arn:aws:iam::{ACCOUNT_ID}:policy/TestGetPolicy"


@mock_iam
def test_get_aws_managed_policy():
    conn = boto3.client("iam", region_name="us-east-1")
    managed_policy_arn = "arn:aws:iam::aws:policy/IAMUserChangePassword"
    managed_policy_create_date = datetime.strptime(
        "2016-11-15T00:25:16+00:00", "%Y-%m-%dT%H:%M:%S+00:00"
    )
    policy = conn.get_policy(PolicyArn=managed_policy_arn)
    assert policy["Policy"]["Arn"] == managed_policy_arn
    assert (
        policy["Policy"]["CreateDate"].replace(tzinfo=None)
        == managed_policy_create_date
    )


@mock_iam
def test_get_policy_version():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_policy(PolicyName="TestGetPolicyVersion", PolicyDocument=MOCK_POLICY)
    version = conn.create_policy_version(
        PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestGetPolicyVersion",
        PolicyDocument=MOCK_POLICY,
    )
    with pytest.raises(ClientError):
        conn.get_policy_version(
            PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestGetPolicyVersion",
            VersionId="v2-does-not-exist",
        )
    retrieved = conn.get_policy_version(
        PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestGetPolicyVersion",
        VersionId=version.get("PolicyVersion")["VersionId"],
    )
    assert retrieved.get("PolicyVersion")["Document"] == json.loads(MOCK_POLICY)
    assert retrieved.get("PolicyVersion")["IsDefaultVersion"] is False


@mock_iam
def test_get_aws_managed_policy_version():
    conn = boto3.client("iam", region_name="us-east-1")
    managed_policy_arn = (
        "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
    )
    managed_policy_version_create_date = datetime.strptime(
        "2015-04-09T15:03:43+00:00", "%Y-%m-%dT%H:%M:%S+00:00"
    )
    with pytest.raises(ClientError):
        conn.get_policy_version(
            PolicyArn=managed_policy_arn, VersionId="v2-does-not-exist"
        )
    retrieved = conn.get_policy_version(PolicyArn=managed_policy_arn, VersionId="v1")
    assert (
        retrieved["PolicyVersion"]["CreateDate"].replace(tzinfo=None)
        == managed_policy_version_create_date
    )
    assert isinstance(retrieved["PolicyVersion"]["Document"], dict)


@mock_iam
def test_get_aws_managed_policy_v6_version():
    conn = boto3.client("iam", region_name="us-east-1")
    managed_policy_arn = "arn:aws:iam::aws:policy/job-function/SystemAdministrator"
    with pytest.raises(ClientError):
        conn.get_policy_version(
            PolicyArn=managed_policy_arn, VersionId="v2-does-not-exist"
        )
    retrieved = conn.get_policy_version(PolicyArn=managed_policy_arn, VersionId="v6")
    assert isinstance(
        retrieved["PolicyVersion"]["CreateDate"].replace(tzinfo=None), datetime
    )
    assert isinstance(retrieved["PolicyVersion"]["Document"], dict)


@mock_iam
def test_list_policy_versions():
    conn = boto3.client("iam", region_name="us-east-1")
    with pytest.raises(ClientError):
        versions = conn.list_policy_versions(
            PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestListPolicyVersions"
        )
    conn.create_policy(PolicyName="TestListPolicyVersions", PolicyDocument=MOCK_POLICY)
    versions = conn.list_policy_versions(
        PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestListPolicyVersions"
    )
    assert versions["Versions"][0]["VersionId"] == "v1"
    assert versions["Versions"][0]["IsDefaultVersion"] is True

    conn.create_policy_version(
        PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestListPolicyVersions",
        PolicyDocument=MOCK_POLICY_2,
    )
    conn.create_policy_version(
        PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestListPolicyVersions",
        PolicyDocument=MOCK_POLICY_3,
    )
    versions = conn.list_policy_versions(
        PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestListPolicyVersions"
    )
    assert versions["Versions"][1]["Document"] == json.loads(MOCK_POLICY_2)
    assert versions["Versions"][1]["IsDefaultVersion"] is False
    assert versions["Versions"][2]["Document"] == json.loads(MOCK_POLICY_3)
    assert versions["Versions"][2]["IsDefaultVersion"] is False


@mock_iam
def test_delete_policy_version():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_policy(PolicyName="TestDeletePolicyVersion", PolicyDocument=MOCK_POLICY)
    conn.create_policy_version(
        PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestDeletePolicyVersion",
        PolicyDocument=MOCK_POLICY,
    )
    with pytest.raises(ClientError):
        conn.delete_policy_version(
            PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestDeletePolicyVersion",
            VersionId="v2-nope-this-does-not-exist",
        )
    conn.delete_policy_version(
        PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestDeletePolicyVersion",
        VersionId="v2",
    )
    versions = conn.list_policy_versions(
        PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestDeletePolicyVersion"
    )
    assert len(versions["Versions"]) == 1


@mock_iam
def test_delete_default_policy_version():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_policy(PolicyName="TestDeletePolicyVersion", PolicyDocument=MOCK_POLICY)
    conn.create_policy_version(
        PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestDeletePolicyVersion",
        PolicyDocument=MOCK_POLICY_2,
    )
    with pytest.raises(ClientError):
        conn.delete_policy_version(
            PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestDeletePolicyVersion",
            VersionId="v1",
        )


@mock_iam()
def test_create_policy_with_tags():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_policy(
        PolicyName="TestCreatePolicyWithTags1",
        PolicyDocument=MOCK_POLICY,
        Tags=[
            {"Key": "somekey", "Value": "somevalue"},
            {"Key": "someotherkey", "Value": "someothervalue"},
        ],
        Description="testing",
    )

    # Get policy:
    policy = conn.get_policy(
        PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestCreatePolicyWithTags1"
    )["Policy"]
    assert len(policy["Tags"]) == 2
    assert policy["Tags"][0]["Key"] == "somekey"
    assert policy["Tags"][0]["Value"] == "somevalue"
    assert policy["Tags"][1]["Key"] == "someotherkey"
    assert policy["Tags"][1]["Value"] == "someothervalue"
    assert policy["Description"] == "testing"


@mock_iam()
def test_create_policy_with_empty_tag_value():
    conn = boto3.client("iam", region_name="us-east-1")

    # Empty is good:
    conn.create_policy(
        PolicyName="TestCreatePolicyWithTags2",
        PolicyDocument=MOCK_POLICY,
        Tags=[{"Key": "somekey", "Value": ""}],
    )
    tags = conn.list_policy_tags(
        PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestCreatePolicyWithTags2"
    )
    assert len(tags["Tags"]) == 1
    assert tags["Tags"][0]["Key"] == "somekey"
    assert tags["Tags"][0]["Value"] == ""


@mock_iam()
def test_create_policy_with_too_many_tags():
    conn = boto3.client("iam", region_name="us-east-1")

    # With more than 50 tags:
    with pytest.raises(ClientError) as ce:
        too_many_tags = list(
            map(lambda x: {"Key": str(x), "Value": str(x)}, range(0, 51))
        )
        conn.create_policy(
            PolicyName="TestCreatePolicyWithTags3",
            PolicyDocument=MOCK_POLICY,
            Tags=too_many_tags,
        )
    assert (
        "failed to satisfy constraint: Member must have length less than or equal to 50."
        in ce.value.response["Error"]["Message"]
    )


@mock_iam()
def test_create_policy_with_duplicate_tag():
    conn = boto3.client("iam", region_name="us-east-1")

    # With a duplicate tag:
    with pytest.raises(ClientError) as ce:
        conn.create_policy(
            PolicyName="TestCreatePolicyWithTags3",
            PolicyDocument=MOCK_POLICY,
            Tags=[{"Key": "0", "Value": ""}, {"Key": "0", "Value": ""}],
        )
    assert (
        "Duplicate tag keys found. Please note that Tag keys are case insensitive."
        in ce.value.response["Error"]["Message"]
    )


@mock_iam()
def test_create_policy_with_duplicate_tag_different_casing():
    conn = boto3.client("iam", region_name="us-east-1")

    # Duplicate tag with different casing:
    with pytest.raises(ClientError) as ce:
        conn.create_policy(
            PolicyName="TestCreatePolicyWithTags3",
            PolicyDocument=MOCK_POLICY,
            Tags=[{"Key": "a", "Value": ""}, {"Key": "A", "Value": ""}],
        )
    assert (
        "Duplicate tag keys found. Please note that Tag keys are case insensitive."
        in ce.value.response["Error"]["Message"]
    )


@mock_iam()
def test_create_policy_with_tag_containing_large_key():
    conn = boto3.client("iam", region_name="us-east-1")

    # With a really big key:
    with pytest.raises(ClientError) as ce:
        conn.create_policy(
            PolicyName="TestCreatePolicyWithTags3",
            PolicyDocument=MOCK_POLICY,
            Tags=[{"Key": "0" * 129, "Value": ""}],
        )
    assert (
        "Member must have length less than or equal to 128."
        in ce.value.response["Error"]["Message"]
    )


@mock_iam()
def test_create_policy_with_tag_containing_large_value():
    conn = boto3.client("iam", region_name="us-east-1")

    # With a really big value:
    with pytest.raises(ClientError) as ce:
        conn.create_policy(
            PolicyName="TestCreatePolicyWithTags3",
            PolicyDocument=MOCK_POLICY,
            Tags=[{"Key": "0", "Value": "0" * 257}],
        )
    assert (
        "Member must have length less than or equal to 256."
        in ce.value.response["Error"]["Message"]
    )


@mock_iam()
def test_create_policy_with_tag_containing_invalid_character():
    conn = boto3.client("iam", region_name="us-east-1")

    # With an invalid character:
    with pytest.raises(ClientError) as ce:
        conn.create_policy(
            PolicyName="TestCreatePolicyWithTags3",
            PolicyDocument=MOCK_POLICY,
            Tags=[{"Key": "NOWAY!", "Value": ""}],
        )
    assert (
        "Member must satisfy regular expression pattern: [\\p{L}\\p{Z}\\p{N}_.:/=+\\-@]+"
        in ce.value.response["Error"]["Message"]
    )


@mock_iam()
def test_create_policy_with_no_tags():
    """Tests both the tag_policy and get_policy_tags capability"""
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_policy(PolicyName="TestTagPolicy", PolicyDocument=MOCK_POLICY)

    # Get without tags:
    policy = conn.get_policy(
        PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestTagPolicy"
    )["Policy"]
    assert not policy.get("Tags")


@mock_iam()
def test_get_policy_with_tags():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_policy(PolicyName="TestTagPolicy", PolicyDocument=MOCK_POLICY)
    conn.tag_policy(
        PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestTagPolicy",
        Tags=[
            {"Key": "somekey", "Value": "somevalue"},
            {"Key": "someotherkey", "Value": "someothervalue"},
        ],
    )

    # Get policy:
    policy = conn.get_policy(
        PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestTagPolicy"
    )["Policy"]
    assert len(policy["Tags"]) == 2
    assert policy["Tags"][0]["Key"] == "somekey"
    assert policy["Tags"][0]["Value"] == "somevalue"
    assert policy["Tags"][1]["Key"] == "someotherkey"
    assert policy["Tags"][1]["Value"] == "someothervalue"


@mock_iam()
def test_list_policy_tags():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_policy(PolicyName="TestTagPolicy", PolicyDocument=MOCK_POLICY)
    conn.tag_policy(
        PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestTagPolicy",
        Tags=[
            {"Key": "somekey", "Value": "somevalue"},
            {"Key": "someotherkey", "Value": "someothervalue"},
        ],
    )

    # List_policy_tags:
    tags = conn.list_policy_tags(
        PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestTagPolicy"
    )
    assert len(tags["Tags"]) == 2
    assert tags["Tags"][0]["Key"] == "somekey"
    assert tags["Tags"][0]["Value"] == "somevalue"
    assert tags["Tags"][1]["Key"] == "someotherkey"
    assert tags["Tags"][1]["Value"] == "someothervalue"
    assert not tags["IsTruncated"]
    assert not tags.get("Marker")


@mock_iam()
def test_list_policy_tags_pagination():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_policy(PolicyName="TestTagPolicy", PolicyDocument=MOCK_POLICY)
    conn.tag_policy(
        PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestTagPolicy",
        Tags=[
            {"Key": "somekey", "Value": "somevalue"},
            {"Key": "someotherkey", "Value": "someothervalue"},
        ],
    )

    # Test pagination:
    tags = conn.list_policy_tags(
        PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestTagPolicy",
        MaxItems=1,
    )
    assert len(tags["Tags"]) == 1
    assert tags["IsTruncated"]
    assert tags["Tags"][0]["Key"] == "somekey"
    assert tags["Tags"][0]["Value"] == "somevalue"
    assert tags["Marker"] == "1"

    tags = conn.list_policy_tags(
        PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestTagPolicy",
        Marker=tags["Marker"],
    )
    assert len(tags["Tags"]) == 1
    assert tags["Tags"][0]["Key"] == "someotherkey"
    assert tags["Tags"][0]["Value"] == "someothervalue"
    assert not tags["IsTruncated"]
    assert not tags.get("Marker")


@mock_iam()
def test_updating_existing_tag():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_policy(PolicyName="TestTagPolicy", PolicyDocument=MOCK_POLICY)
    conn.tag_policy(
        PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestTagPolicy",
        Tags=[
            {"Key": "somekey", "Value": "somevalue"},
            {"Key": "someotherkey", "Value": "someothervalue"},
        ],
    )

    # Test updating an existing tag:
    conn.tag_policy(
        PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestTagPolicy",
        Tags=[{"Key": "somekey", "Value": "somenewvalue"}],
    )
    tags = conn.list_policy_tags(
        PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestTagPolicy"
    )
    assert len(tags["Tags"]) == 2
    assert tags["Tags"][0]["Key"] == "somekey"
    assert tags["Tags"][0]["Value"] == "somenewvalue"


@mock_iam()
def test_updating_existing_tag_with_empty_value():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_policy(PolicyName="TestTagPolicy", PolicyDocument=MOCK_POLICY)
    conn.tag_policy(
        PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestTagPolicy",
        Tags=[
            {"Key": "somekey", "Value": "somevalue"},
            {"Key": "someotherkey", "Value": "someothervalue"},
        ],
    )

    # Empty is good:
    conn.tag_policy(
        PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestTagPolicy",
        Tags=[{"Key": "somekey", "Value": ""}],
    )
    tags = conn.list_policy_tags(
        PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestTagPolicy"
    )
    assert len(tags["Tags"]) == 2
    assert tags["Tags"][0]["Key"] == "somekey"
    assert tags["Tags"][0]["Value"] == ""


@mock_iam()
def test_updating_existing_tagged_policy_with_too_many_tags():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_policy(PolicyName="TestTagPolicy", PolicyDocument=MOCK_POLICY)
    conn.tag_policy(
        PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestTagPolicy",
        Tags=[
            {"Key": "somekey", "Value": "somevalue"},
            {"Key": "someotherkey", "Value": "someothervalue"},
        ],
    )

    # With more than 50 tags:
    with pytest.raises(ClientError) as ce:
        too_many_tags = list(
            map(lambda x: {"Key": str(x), "Value": str(x)}, range(0, 51))
        )
        conn.tag_policy(
            PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestTagPolicy",
            Tags=too_many_tags,
        )
    assert (
        "failed to satisfy constraint: Member must have length less than or equal to 50."
        in ce.value.response["Error"]["Message"]
    )


@mock_iam()
def test_updating_existing_tagged_policy_with_duplicate_tag():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_policy(PolicyName="TestTagPolicy", PolicyDocument=MOCK_POLICY)
    conn.tag_policy(
        PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestTagPolicy",
        Tags=[
            {"Key": "somekey", "Value": "somevalue"},
            {"Key": "someotherkey", "Value": "someothervalue"},
        ],
    )

    # With a duplicate tag:
    with pytest.raises(ClientError) as ce:
        conn.tag_policy(
            PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestTagPolicy",
            Tags=[{"Key": "0", "Value": ""}, {"Key": "0", "Value": ""}],
        )
    assert (
        "Duplicate tag keys found. Please note that Tag keys are case insensitive."
        in ce.value.response["Error"]["Message"]
    )


@mock_iam()
def test_updating_existing_tagged_policy_with_duplicate_tag_different_casing():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_policy(PolicyName="TestTagPolicy", PolicyDocument=MOCK_POLICY)
    conn.tag_policy(
        PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestTagPolicy",
        Tags=[
            {"Key": "somekey", "Value": "somevalue"},
            {"Key": "someotherkey", "Value": "someothervalue"},
        ],
    )

    # Duplicate tag with different casing:
    with pytest.raises(ClientError) as ce:
        conn.tag_policy(
            PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestTagPolicy",
            Tags=[{"Key": "a", "Value": ""}, {"Key": "A", "Value": ""}],
        )
    assert (
        "Duplicate tag keys found. Please note that Tag keys are case insensitive."
        in ce.value.response["Error"]["Message"]
    )


@mock_iam()
def test_updating_existing_tagged_policy_with_large_key():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_policy(PolicyName="TestTagPolicy", PolicyDocument=MOCK_POLICY)
    conn.tag_policy(
        PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestTagPolicy",
        Tags=[
            {"Key": "somekey", "Value": "somevalue"},
            {"Key": "someotherkey", "Value": "someothervalue"},
        ],
    )

    # With a really big key:
    with pytest.raises(ClientError) as ce:
        conn.tag_policy(
            PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestTagPolicy",
            Tags=[{"Key": "0" * 129, "Value": ""}],
        )
    assert (
        "Member must have length less than or equal to 128."
        in ce.value.response["Error"]["Message"]
    )


@mock_iam()
def test_updating_existing_tagged_policy_with_large_value():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_policy(PolicyName="TestTagPolicy", PolicyDocument=MOCK_POLICY)
    conn.tag_policy(
        PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestTagPolicy",
        Tags=[
            {"Key": "somekey", "Value": "somevalue"},
            {"Key": "someotherkey", "Value": "someothervalue"},
        ],
    )

    # With a really big value:
    with pytest.raises(ClientError) as ce:
        conn.tag_policy(
            PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestTagPolicy",
            Tags=[{"Key": "0", "Value": "0" * 257}],
        )
    assert (
        "Member must have length less than or equal to 256."
        in ce.value.response["Error"]["Message"]
    )


@mock_iam()
def test_updating_existing_tagged_policy_with_invalid_character():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_policy(PolicyName="TestTagPolicy", PolicyDocument=MOCK_POLICY)
    conn.tag_policy(
        PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestTagPolicy",
        Tags=[
            {"Key": "somekey", "Value": "somevalue"},
            {"Key": "someotherkey", "Value": "someothervalue"},
        ],
    )

    # With an invalid character:
    with pytest.raises(ClientError) as ce:
        conn.tag_policy(
            PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestTagPolicy",
            Tags=[{"Key": "NOWAY!", "Value": ""}],
        )
    assert (
        "Member must satisfy regular expression pattern: [\\p{L}\\p{Z}\\p{N}_.:/=+\\-@]+"
        in ce.value.response["Error"]["Message"]
    )


@mock_iam()
def test_tag_non_existant_policy():
    conn = boto3.client("iam", region_name="us-east-1")

    # With a policy that doesn't exist:
    with pytest.raises(ClientError):
        conn.tag_policy(
            PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/NotAPolicy",
            Tags=[{"Key": "some", "Value": "value"}],
        )


@mock_iam
def test_untag_policy():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_policy(PolicyName="TestUnTagPolicy", PolicyDocument=MOCK_POLICY)

    # With proper tag values:
    conn.tag_policy(
        PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestUnTagPolicy",
        Tags=[
            {"Key": "somekey", "Value": "somevalue"},
            {"Key": "someotherkey", "Value": "someothervalue"},
        ],
    )

    # Remove them:
    conn.untag_policy(
        PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestUnTagPolicy",
        TagKeys=["somekey"],
    )
    tags = conn.list_policy_tags(
        PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestUnTagPolicy"
    )
    assert len(tags["Tags"]) == 1
    assert tags["Tags"][0]["Key"] == "someotherkey"
    assert tags["Tags"][0]["Value"] == "someothervalue"

    # And again:
    conn.untag_policy(
        PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestUnTagPolicy",
        TagKeys=["someotherkey"],
    )
    tags = conn.list_policy_tags(
        PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestUnTagPolicy"
    )
    assert not tags["Tags"]

    # Test removing tags with invalid values:
    # With more than 50 tags:
    with pytest.raises(ClientError) as ce:
        conn.untag_policy(
            PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestUnTagPolicy",
            TagKeys=[str(x) for x in range(0, 51)],
        )
    assert (
        "failed to satisfy constraint: Member must have length less than or equal to 50."
        in ce.value.response["Error"]["Message"]
    )
    assert "tagKeys" in ce.value.response["Error"]["Message"]

    # With a really big key:
    with pytest.raises(ClientError) as ce:
        conn.untag_policy(
            PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestUnTagPolicy",
            TagKeys=["0" * 129],
        )
    assert (
        "Member must have length less than or equal to 128."
        in ce.value.response["Error"]["Message"]
    )
    assert "tagKeys" in ce.value.response["Error"]["Message"]

    # With an invalid character:
    with pytest.raises(ClientError) as ce:
        conn.untag_policy(
            PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/TestUnTagPolicy",
            TagKeys=["NOWAY!"],
        )
    assert (
        "Member must satisfy regular expression pattern: [\\p{L}\\p{Z}\\p{N}_.:/=+\\-@]+"
        in ce.value.response["Error"]["Message"]
    )
    assert "tagKeys" in ce.value.response["Error"]["Message"]

    # With a policy that doesn't exist:
    with pytest.raises(ClientError):
        conn.untag_policy(
            PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/NotAPolicy",
            TagKeys=["somevalue"],
        )


@mock_iam
def test_create_user_boto():
    conn = boto3.client("iam", region_name="us-east-1")
    u = conn.create_user(UserName="my-user")["User"]
    assert u["Path"] == "/"
    assert u["UserName"] == "my-user"
    assert "UserId" in u
    assert u["Arn"] == f"arn:aws:iam::{ACCOUNT_ID}:user/my-user"
    assert isinstance(u["CreateDate"], datetime)

    with pytest.raises(ClientError) as ex:
        conn.create_user(UserName="my-user")
    err = ex.value.response["Error"]
    assert err["Code"] == "EntityAlreadyExists"
    assert err["Message"] == "User my-user already exists"


@mock_iam
def test_get_user():
    conn = boto3.client("iam", region_name="us-east-1")
    with pytest.raises(ClientError) as ex:
        conn.get_user(UserName="my-user")
    err = ex.value.response["Error"]
    assert err["Code"] == "NoSuchEntity"
    assert err["Message"] == "The user with name my-user cannot be found."

    conn.create_user(UserName="my-user")

    u = conn.get_user(UserName="my-user")["User"]
    assert u["Path"] == "/"
    assert u["UserName"] == "my-user"
    assert "UserId" in u
    assert u["Arn"] == f"arn:aws:iam::{ACCOUNT_ID}:user/my-user"
    assert isinstance(u["CreateDate"], datetime)


@mock_iam()
def test_update_user():
    conn = boto3.client("iam", region_name="us-east-1")
    with pytest.raises(conn.exceptions.NoSuchEntityException):
        conn.update_user(UserName="my-user")
    conn.create_user(UserName="my-user")
    conn.update_user(UserName="my-user", NewPath="/new-path/", NewUserName="new-user")
    response = conn.get_user(UserName="new-user")
    assert response["User"]["Path"] == "/new-path/"
    with pytest.raises(conn.exceptions.NoSuchEntityException):
        conn.get_user(UserName="my-user")


@mock_iam
def test_get_current_user():
    """If no user is specific, IAM returns the current user"""
    conn = boto3.client("iam", region_name="us-east-1")
    user = conn.get_user()["User"]
    assert user["UserName"] == "default_user"


@mock_iam()
def test_list_users():
    path_prefix = "/"
    max_items = 10
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_user(UserName="my-user")
    response = conn.list_users(PathPrefix=path_prefix, MaxItems=max_items)
    user = response["Users"][0]
    assert user["UserName"] == "my-user"
    assert user["Path"] == "/"
    assert user["Arn"] == f"arn:aws:iam::{ACCOUNT_ID}:user/my-user"
    assert response["IsTruncated"] is False

    conn.create_user(UserName="my-user-1", Path="myUser")
    response = conn.list_users(PathPrefix="my")
    user = response["Users"][0]
    assert user["UserName"] == "my-user-1"
    assert user["Path"] == "myUser"


@mock_iam()
def test_user_policies():
    policy_name = "UserManagedPolicy"
    user_name = "my-user"
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_user(UserName=user_name)
    conn.put_user_policy(
        UserName=user_name, PolicyName=policy_name, PolicyDocument=MOCK_POLICY
    )

    policy_doc = conn.get_user_policy(UserName=user_name, PolicyName=policy_name)
    assert policy_doc["PolicyDocument"] == json.loads(MOCK_POLICY)

    policies = conn.list_user_policies(UserName=user_name)
    assert len(policies["PolicyNames"]) == 1
    assert policies["PolicyNames"][0] == policy_name

    conn.delete_user_policy(UserName=user_name, PolicyName=policy_name)

    policies = conn.list_user_policies(UserName=user_name)
    assert len(policies["PolicyNames"]) == 0


@mock_iam
def test_create_login_profile_with_unknown_user():
    conn = boto3.client("iam", region_name="us-east-1")
    with pytest.raises(ClientError) as ex:
        conn.create_login_profile(UserName="my-user", Password="my-pass")
    err = ex.value.response["Error"]
    assert err["Code"] == "NoSuchEntity"
    assert err["Message"] == "The user with name my-user cannot be found."


@mock_iam
def test_delete_login_profile_with_unknown_user():
    conn = boto3.client("iam", region_name="us-east-1")
    with pytest.raises(ClientError) as ex:
        conn.delete_login_profile(UserName="my-user")
    err = ex.value.response["Error"]
    assert err["Code"] == "NoSuchEntity"
    assert err["Message"] == "The user with name my-user cannot be found."


@mock_iam
def test_delete_nonexistent_login_profile():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_user(UserName="my-user")
    with pytest.raises(ClientError) as ex:
        conn.delete_login_profile(UserName="my-user")
    err = ex.value.response["Error"]
    assert err["Code"] == "NoSuchEntity"
    assert err["Message"] == "Login profile for my-user not found"


@mock_iam
def test_delete_login_profile():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_user(UserName="my-user")
    conn.create_login_profile(UserName="my-user", Password="my-pass")
    conn.delete_login_profile(UserName="my-user")

    with pytest.raises(ClientError):
        conn.get_login_profile(UserName="my-user")


@mock_iam
def test_create_access_key():
    conn = boto3.client("iam", region_name="us-east-1")
    with pytest.raises(ClientError):
        conn.create_access_key(UserName="my-user")
    conn.create_user(UserName="my-user")
    access_key = conn.create_access_key(UserName="my-user")["AccessKey"]
    assert 0 <= (utcnow() - access_key["CreateDate"].replace(tzinfo=None)).seconds < 10
    assert len(access_key["AccessKeyId"]) == 20
    assert len(access_key["SecretAccessKey"]) == 40
    assert access_key["AccessKeyId"].startswith("AKIA")
    conn = boto3.client(
        "iam",
        region_name="us-east-1",
        aws_access_key_id=access_key["AccessKeyId"],
        aws_secret_access_key=access_key["SecretAccessKey"],
    )
    access_key = conn.create_access_key()["AccessKey"]
    assert 0 <= (utcnow() - access_key["CreateDate"].replace(tzinfo=None)).seconds < 10
    assert len(access_key["AccessKeyId"]) == 20
    assert len(access_key["SecretAccessKey"]) == 40
    assert access_key["AccessKeyId"].startswith("AKIA")


@mock_iam
def test_limit_access_key_per_user():
    conn = boto3.client("iam", region_name=DEFAULT_REGION_NAME)
    user_name = "test-user"
    conn.create_user(UserName=user_name)

    conn.create_access_key(UserName=user_name)
    conn.create_access_key(UserName=user_name)
    with pytest.raises(ClientError) as ex:
        conn.create_access_key(UserName=user_name)

    err = ex.value.response["Error"]
    assert err["Code"] == "LimitExceeded"
    assert err["Message"] == "Cannot exceed quota for AccessKeysPerUser: 2"


@mock_iam
def test_list_access_keys():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_user(UserName="my-user")
    response = conn.list_access_keys(UserName="my-user")
    assert response["AccessKeyMetadata"] == []
    access_key = conn.create_access_key(UserName="my-user")["AccessKey"]
    response = conn.list_access_keys(UserName="my-user")
    assert sorted(response["AccessKeyMetadata"][0].keys()) == sorted(
        ["Status", "CreateDate", "UserName", "AccessKeyId"]
    )
    conn = boto3.client(
        "iam",
        region_name="us-east-1",
        aws_access_key_id=access_key["AccessKeyId"],
        aws_secret_access_key=access_key["SecretAccessKey"],
    )
    response = conn.list_access_keys()
    assert sorted(response["AccessKeyMetadata"][0].keys()) == sorted(
        ["Status", "CreateDate", "UserName", "AccessKeyId"]
    )


@mock_iam
def test_delete_access_key():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_user(UserName="my-user")
    key = conn.create_access_key(UserName="my-user")["AccessKey"]
    conn.delete_access_key(AccessKeyId=key["AccessKeyId"], UserName="my-user")
    key = conn.create_access_key(UserName="my-user")["AccessKey"]
    conn.delete_access_key(AccessKeyId=key["AccessKeyId"])


@mock_iam()
def test_mfa_devices():
    # Test enable device
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_user(UserName="my-user")
    conn.enable_mfa_device(
        UserName="my-user",
        SerialNumber="123456789",
        AuthenticationCode1="234567",
        AuthenticationCode2="987654",
    )

    # Test list mfa devices
    response = conn.list_mfa_devices(UserName="my-user")
    device = response["MFADevices"][0]
    assert device["SerialNumber"] == "123456789"

    # Test deactivate mfa device
    conn.deactivate_mfa_device(UserName="my-user", SerialNumber="123456789")
    response = conn.list_mfa_devices(UserName="my-user")
    assert len(response["MFADevices"]) == 0


@mock_iam
def test_create_virtual_mfa_device():
    client = boto3.client("iam", region_name="us-east-1")
    response = client.create_virtual_mfa_device(VirtualMFADeviceName="test-device")
    device = response["VirtualMFADevice"]

    assert device["SerialNumber"] == f"arn:aws:iam::{ACCOUNT_ID}:mfa/test-device"
    device["Base32StringSeed"].decode("ascii")
    assert device["QRCodePNG"] != ""

    response = client.create_virtual_mfa_device(
        Path="/", VirtualMFADeviceName="test-device-2"
    )
    device = response["VirtualMFADevice"]

    assert device["SerialNumber"] == f"arn:aws:iam::{ACCOUNT_ID}:mfa/test-device-2"
    device["Base32StringSeed"].decode("ascii")
    assert device["QRCodePNG"] != ""

    response = client.create_virtual_mfa_device(
        Path="/test/", VirtualMFADeviceName="test-device"
    )
    device = response["VirtualMFADevice"]

    assert device["SerialNumber"] == f"arn:aws:iam::{ACCOUNT_ID}:mfa/test/test-device"
    device["Base32StringSeed"].decode("ascii")
    assert device["QRCodePNG"] != ""
    assert isinstance(device["QRCodePNG"], bytes)


@mock_iam
def test_create_virtual_mfa_device_errors():
    client = boto3.client("iam", region_name="us-east-1")
    client.create_virtual_mfa_device(VirtualMFADeviceName="test-device")

    with pytest.raises(ClientError) as exc:
        client.create_virtual_mfa_device(VirtualMFADeviceName="test-device")
    err = exc.value.response["Error"]
    assert (
        err["Message"] == "MFADevice entity at the same path and name already exists."
    )

    with pytest.raises(ClientError) as exc:
        client.create_virtual_mfa_device(
            Path="test", VirtualMFADeviceName="test-device"
        )
    err = exc.value.response["Error"]
    assert (
        err["Message"]
        == "The specified value for path is invalid. It must begin and end with / and contain only alphanumeric characters and/or / characters."
    )

    with pytest.raises(ClientError) as exc:
        client.create_virtual_mfa_device(
            Path="/test//test/", VirtualMFADeviceName="test-device"
        )
    err = exc.value.response["Error"]
    assert (
        err["Message"]
        == "The specified value for path is invalid. It must begin and end with / and contain only alphanumeric characters and/or / characters."
    )

    too_long_path = f"/{('b' * 511)}/"
    with pytest.raises(ClientError) as exc:
        client.create_virtual_mfa_device(
            Path=too_long_path, VirtualMFADeviceName="test-device"
        )
    err = exc.value.response["Error"]
    assert (
        err["Message"]
        == '1 validation error detected: Value "{}" at "path" failed to satisfy constraint: Member must have length less than or equal to 512'
    )


@mock_iam
def test_delete_virtual_mfa_device():
    client = boto3.client("iam", region_name="us-east-1")
    response = client.create_virtual_mfa_device(VirtualMFADeviceName="test-device")
    serial_number = response["VirtualMFADevice"]["SerialNumber"]

    client.delete_virtual_mfa_device(SerialNumber=serial_number)

    response = client.list_virtual_mfa_devices()

    assert len(response["VirtualMFADevices"]) == 0
    assert response["IsTruncated"] is False


@mock_iam
def test_delete_virtual_mfa_device_errors():
    client = boto3.client("iam", region_name="us-east-1")

    serial_number = f"arn:aws:iam::{ACCOUNT_ID}:mfa/not-existing"
    with pytest.raises(ClientError) as exc:
        client.delete_virtual_mfa_device(SerialNumber=serial_number)
    err = exc.value.response["Error"]
    assert (
        err["Message"]
        == f"VirtualMFADevice with serial number {serial_number} doesn't exist."
    )


@mock_iam
def test_list_virtual_mfa_devices():
    client = boto3.client("iam", region_name="us-east-1")
    response = client.create_virtual_mfa_device(VirtualMFADeviceName="test-device")
    serial_number_1 = response["VirtualMFADevice"]["SerialNumber"]

    response = client.create_virtual_mfa_device(
        Path="/test/", VirtualMFADeviceName="test-device"
    )
    serial_number_2 = response["VirtualMFADevice"]["SerialNumber"]

    response = client.list_virtual_mfa_devices()

    assert response["VirtualMFADevices"] == [
        {"SerialNumber": serial_number_1},
        {"SerialNumber": serial_number_2},
    ]
    assert response["IsTruncated"] is False

    response = client.list_virtual_mfa_devices(AssignmentStatus="Assigned")

    assert len(response["VirtualMFADevices"]) == 0
    assert response["IsTruncated"] is False

    response = client.list_virtual_mfa_devices(AssignmentStatus="Unassigned")

    assert response["VirtualMFADevices"] == [
        {"SerialNumber": serial_number_1},
        {"SerialNumber": serial_number_2},
    ]
    assert response["IsTruncated"] is False

    response = client.list_virtual_mfa_devices(AssignmentStatus="Any", MaxItems=1)

    assert response["VirtualMFADevices"] == [{"SerialNumber": serial_number_1}]
    assert response["IsTruncated"] is True
    assert response["Marker"] == "1"

    response = client.list_virtual_mfa_devices(
        AssignmentStatus="Any", Marker=response["Marker"]
    )

    assert response["VirtualMFADevices"] == [{"SerialNumber": serial_number_2}]
    assert response["IsTruncated"] is False


@mock_iam
def test_list_virtual_mfa_devices_errors():
    client = boto3.client("iam", region_name="us-east-1")
    client.create_virtual_mfa_device(VirtualMFADeviceName="test-device")

    with pytest.raises(ClientError) as exc:
        client.list_virtual_mfa_devices(Marker="100")
    err = exc.value.response["Error"]
    assert err["Message"] == "Invalid Marker."


@mock_iam
def test_enable_virtual_mfa_device():
    client = boto3.client("iam", region_name="us-east-1")
    response = client.create_virtual_mfa_device(VirtualMFADeviceName="test-device")
    serial_number = response["VirtualMFADevice"]["SerialNumber"]
    tags = [{"Key": "key", "Value": "value"}]

    client.create_user(UserName="test-user", Tags=tags)
    client.enable_mfa_device(
        UserName="test-user",
        SerialNumber=serial_number,
        AuthenticationCode1="234567",
        AuthenticationCode2="987654",
    )

    response = client.list_virtual_mfa_devices(AssignmentStatus="Unassigned")

    assert len(response["VirtualMFADevices"]) == 0
    assert response["IsTruncated"] is False

    response = client.list_virtual_mfa_devices(AssignmentStatus="Assigned")

    device = response["VirtualMFADevices"][0]
    assert device["SerialNumber"] == serial_number
    assert device["User"]["Path"] == "/"
    assert device["User"]["UserName"] == "test-user"
    assert device["User"]["Arn"] == f"arn:aws:iam::{ACCOUNT_ID}:user/test-user"
    assert isinstance(device["User"]["CreateDate"], datetime)
    assert device["User"]["Tags"] == tags
    assert isinstance(device["EnableDate"], datetime)
    assert response["IsTruncated"] is False

    client.deactivate_mfa_device(UserName="test-user", SerialNumber=serial_number)

    response = client.list_virtual_mfa_devices(AssignmentStatus="Assigned")

    assert len(response["VirtualMFADevices"]) == 0
    assert response["IsTruncated"] is False

    response = client.list_virtual_mfa_devices(AssignmentStatus="Unassigned")

    assert response["VirtualMFADevices"] == [{"SerialNumber": serial_number}]
    assert response["IsTruncated"] is False


@mock_iam()
def test_delete_user():
    conn = boto3.client("iam", region_name="us-east-1")
    with pytest.raises(conn.exceptions.NoSuchEntityException):
        conn.delete_user(UserName="my-user")

    # Test deletion failure with a managed policy
    conn.create_user(UserName="my-user")
    response = conn.create_policy(
        PolicyName="my-managed-policy", PolicyDocument=MOCK_POLICY
    )
    conn.attach_user_policy(PolicyArn=response["Policy"]["Arn"], UserName="my-user")
    with pytest.raises(conn.exceptions.DeleteConflictException):
        conn.delete_user(UserName="my-user")
    conn.detach_user_policy(PolicyArn=response["Policy"]["Arn"], UserName="my-user")
    conn.delete_policy(PolicyArn=response["Policy"]["Arn"])
    conn.delete_user(UserName="my-user")
    with pytest.raises(conn.exceptions.NoSuchEntityException):
        conn.get_user(UserName="my-user")

    # Test deletion failure with an inline policy
    conn.create_user(UserName="my-user")
    conn.put_user_policy(
        UserName="my-user", PolicyName="my-user-policy", PolicyDocument=MOCK_POLICY
    )
    with pytest.raises(conn.exceptions.DeleteConflictException):
        conn.delete_user(UserName="my-user")
    conn.delete_user_policy(UserName="my-user", PolicyName="my-user-policy")
    conn.delete_user(UserName="my-user")
    with pytest.raises(conn.exceptions.NoSuchEntityException):
        conn.get_user(UserName="my-user")

    # Test deletion with no conflicts
    conn.create_user(UserName="my-user")
    conn.delete_user(UserName="my-user")
    with pytest.raises(conn.exceptions.NoSuchEntityException):
        conn.get_user(UserName="my-user")


@mock_iam
def test_generate_credential_report():
    conn = boto3.client("iam", region_name="us-east-1")
    result = conn.generate_credential_report()
    assert result["State"] == "STARTED"
    result = conn.generate_credential_report()
    assert result["State"] == "COMPLETE"


@mock_iam
def test_get_credential_report():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_user(UserName="my-user")
    with pytest.raises(ClientError):
        conn.get_credential_report()
    result = conn.generate_credential_report()
    while result["State"] != "COMPLETE":
        result = conn.generate_credential_report()
    result = conn.get_credential_report()
    report = result["Content"].decode("utf-8")
    assert "my-user" in report


@mock_iam
def test_get_credential_report_content():
    conn = boto3.client("iam", region_name="us-east-1")
    username = "my-user"
    conn.create_user(UserName=username)
    conn.create_login_profile(UserName=username, Password="123")
    key1 = conn.create_access_key(UserName=username)["AccessKey"]
    conn.update_access_key(
        UserName=username, AccessKeyId=key1["AccessKeyId"], Status="Inactive"
    )
    key1 = conn.create_access_key(UserName=username)["AccessKey"]
    timestamp = utcnow()
    if not settings.TEST_SERVER_MODE:
        iam_backend = get_backend("iam")[ACCOUNT_ID]["global"]
        iam_backend.users[username].access_keys[1].last_used = timestamp
        iam_backend.users[username].password_last_used = timestamp
    with pytest.raises(ClientError):
        conn.get_credential_report()
    result = conn.generate_credential_report()
    while result["State"] != "COMPLETE":
        result = conn.generate_credential_report()
    result = conn.get_credential_report()
    report = result["Content"].decode("utf-8")
    header = report.split("\n")[0]
    assert (
        header
        == "user,arn,user_creation_time,password_enabled,password_last_used,password_last_changed,password_next_rotation,mfa_active,access_key_1_active,access_key_1_last_rotated,access_key_1_last_used_date,access_key_1_last_used_region,access_key_1_last_used_service,access_key_2_active,access_key_2_last_rotated,access_key_2_last_used_date,access_key_2_last_used_region,access_key_2_last_used_service,cert_1_active,cert_1_last_rotated,cert_2_active,cert_2_last_rotated"
    )
    report_dict = csv.DictReader(report.split("\n"))
    user = next(report_dict)
    assert user["user"] == "my-user"
    assert user["access_key_1_active"] == "false"
    assert timestamp.strftime("%Y-%m-%d") in user["access_key_1_last_rotated"]
    assert user["access_key_1_last_used_date"] == "N/A"
    assert user["access_key_2_active"] == "true"
    if not settings.TEST_SERVER_MODE:
        assert timestamp.strftime("%Y-%m-%d") in user["access_key_2_last_used_date"]
        assert timestamp.strftime("%Y-%m-%d") in user["password_last_used"]
    else:
        assert user["access_key_2_last_used_date"] == "N/A"
        assert user["password_last_used"] == "no_information"


@mock_iam
def test_get_access_key_last_used_when_used():
    iam = boto3.resource("iam", region_name="us-east-1")
    client = iam.meta.client
    username = "test-user"
    iam.create_user(UserName=username)
    with pytest.raises(ClientError):
        client.get_access_key_last_used(AccessKeyId="non-existent-key-id")
    create_key_response = client.create_access_key(UserName=username)["AccessKey"]

    access_key_client = boto3.client(
        "iam",
        region_name="us-east-1",
        aws_access_key_id=create_key_response["AccessKeyId"],
        aws_secret_access_key=create_key_response["SecretAccessKey"],
    )
    access_key_client.list_users()

    resp = client.get_access_key_last_used(
        AccessKeyId=create_key_response["AccessKeyId"]
    )
    assert "LastUsedDate" in resp["AccessKeyLastUsed"]
    assert resp["AccessKeyLastUsed"]["ServiceName"] == "iam"
    assert resp["AccessKeyLastUsed"]["Region"] == "us-east-1"


@mock_iam
def test_managed_policy():
    conn = boto3.client("iam", region_name="us-west-1")

    conn.create_policy(
        PolicyName="UserManagedPolicy",
        PolicyDocument=MOCK_POLICY,
        Path="/mypolicy/",
        Description="my user managed policy",
    )

    marker = "0"
    aws_policies = []
    while marker is not None:
        response = conn.list_policies(Scope="AWS", Marker=marker)
        for policy in response["Policies"]:
            aws_policies.append(policy)
        marker = response.get("Marker")
    aws_managed_policies = iam_backends[ACCOUNT_ID]["global"].aws_managed_policies
    assert set(p.name for p in aws_managed_policies) == set(
        p["PolicyName"] for p in aws_policies
    )

    user_policies = conn.list_policies(Scope="Local")["Policies"]
    assert set(["UserManagedPolicy"]) == set(p["PolicyName"] for p in user_policies)

    marker = "0"
    all_policies = []
    while marker is not None:
        response = conn.list_policies(Marker=marker)
        for policy in response["Policies"]:
            all_policies.append(policy)
        marker = response.get("Marker")
    assert set(p["PolicyName"] for p in aws_policies + user_policies) == set(
        p["PolicyName"] for p in all_policies
    )

    role_name = "my-new-role"
    conn.create_role(
        RoleName=role_name, AssumeRolePolicyDocument="test policy", Path="my-path"
    )
    for policy_name in [
        "AmazonElasticMapReduceRole",
        "AWSControlTowerServiceRolePolicy",
    ]:
        policy_arn = "arn:aws:iam::aws:policy/service-role/" + policy_name
        conn.attach_role_policy(PolicyArn=policy_arn, RoleName=role_name)

    rows = conn.list_policies(OnlyAttached=True)["Policies"]
    assert len(rows) == 2
    for x in rows:
        assert x["AttachmentCount"] > 0

    resp = conn.list_attached_role_policies(RoleName=role_name)
    assert len(resp["AttachedPolicies"]) == 2

    conn.detach_role_policy(
        PolicyArn="arn:aws:iam::aws:policy/service-role/AmazonElasticMapReduceRole",
        RoleName=role_name,
    )
    rows = conn.list_policies(OnlyAttached=True)["Policies"]
    assert "AWSControlTowerServiceRolePolicy" in [r["PolicyName"] for r in rows]
    assert "AmazonElasticMapReduceRole" not in [r["PolicyName"] for r in rows]
    for x in rows:
        assert x["AttachmentCount"] > 0

    policies = conn.list_attached_role_policies(RoleName=role_name)["AttachedPolicies"]
    assert "AWSControlTowerServiceRolePolicy" in [p["PolicyName"] for p in policies]
    assert "AmazonElasticMapReduceRole" not in [p["PolicyName"] for p in policies]

    with pytest.raises(ClientError) as ex:
        conn.detach_role_policy(
            PolicyArn="arn:aws:iam::aws:policy/service-role/AmazonElasticMapReduceRole",
            RoleName=role_name,
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "NoSuchEntity"
    assert (
        err["Message"]
        == "Policy arn:aws:iam::aws:policy/service-role/AmazonElasticMapReduceRole was not found."
    )

    with pytest.raises(ClientError) as ex:
        conn.detach_role_policy(
            PolicyArn="arn:aws:iam::aws:policy/Nonexistent", RoleName=role_name
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "NoSuchEntity"
    assert err["Message"] == "Policy arn:aws:iam::aws:policy/Nonexistent was not found."


@mock_iam
def test_create_login_profile__duplicate():
    conn = boto3.client("iam", region_name="us-east-1")

    conn.create_user(UserName="my-user")
    conn.create_login_profile(UserName="my-user", Password="Password")

    with pytest.raises(ClientError) as exc:
        conn.create_login_profile(UserName="my-user", Password="my-pass")
    err = exc.value.response["Error"]
    assert err["Code"] == "User my-user already has password"
    assert err["Message"] is None


@mock_iam()
def test_attach_detach_user_policy():
    iam = boto3.resource("iam", region_name="us-east-1")
    client = boto3.client("iam", region_name="us-east-1")

    user = iam.create_user(UserName="test-user")

    policy_name = "UserAttachedPolicy"
    policy = iam.create_policy(
        PolicyName=policy_name,
        PolicyDocument=MOCK_POLICY,
        Path="/mypolicy/",
        Description="my user attached policy",
    )

    # try a non-existent policy
    non_existent_policy_arn = f"arn:aws:iam::{ACCOUNT_ID}:policy/not-existent"
    with pytest.raises(ClientError) as exc:
        client.attach_user_policy(UserName=user.name, PolicyArn=non_existent_policy_arn)
    err = exc.value.response["Error"]
    assert err["Code"] == "NoSuchEntity"
    assert (
        err["Message"]
        == f"Policy {non_existent_policy_arn} does not exist or is not attachable."
    )

    client.attach_user_policy(UserName=user.name, PolicyArn=policy.arn)

    resp = client.list_attached_user_policies(UserName=user.name)
    assert len(resp["AttachedPolicies"]) == 1
    attached_policy = resp["AttachedPolicies"][0]
    assert attached_policy["PolicyArn"] == policy.arn
    assert attached_policy["PolicyName"] == policy_name

    client.detach_user_policy(UserName=user.name, PolicyArn=policy.arn)

    resp = client.list_attached_user_policies(UserName=user.name)
    assert len(resp["AttachedPolicies"]) == 0


@mock_iam()
def test_attach_detach_role_policy():
    iam = boto3.resource("iam", region_name="us-east-1")
    client = boto3.client("iam", region_name="us-east-1")

    role = iam.create_role(RoleName="test-role", AssumeRolePolicyDocument="{}")

    policy_name = "RoleAttachedPolicy"
    policy = iam.create_policy(
        PolicyName=policy_name,
        PolicyDocument=MOCK_POLICY,
        Path="/mypolicy/",
        Description="my role attached policy",
    )

    # try a non-existent policy
    non_existent_policy_arn = f"arn:aws:iam::{ACCOUNT_ID}:policy/not-existent"
    with pytest.raises(ClientError) as exc:
        client.attach_role_policy(RoleName=role.name, PolicyArn=non_existent_policy_arn)
    err = exc.value.response["Error"]
    assert err["Code"] == "NoSuchEntity"
    assert (
        err["Message"]
        == f"Policy {non_existent_policy_arn} does not exist or is not attachable."
    )

    client.attach_role_policy(RoleName=role.name, PolicyArn=policy.arn)

    resp = client.list_attached_role_policies(RoleName=role.name)
    assert len(resp["AttachedPolicies"]) == 1
    attached_policy = resp["AttachedPolicies"][0]
    assert attached_policy["PolicyArn"] == policy.arn
    assert attached_policy["PolicyName"] == policy_name

    client.detach_role_policy(RoleName=role.name, PolicyArn=policy.arn)

    resp = client.list_attached_role_policies(RoleName=role.name)
    assert len(resp["AttachedPolicies"]) == 0


@mock_iam()
def test_only_detach_user_policy():
    iam = boto3.resource("iam", region_name="us-east-1")
    client = boto3.client("iam", region_name="us-east-1")

    user = iam.create_user(UserName="test-user")

    policy_name = "FreePolicy"
    policy = iam.create_policy(
        PolicyName=policy_name,
        PolicyDocument=MOCK_POLICY,
        Path="/mypolicy/",
        Description="free floating policy",
    )

    resp = client.list_attached_user_policies(UserName=user.name)
    assert len(resp["AttachedPolicies"]) == 0

    with pytest.raises(ClientError) as exc:
        client.detach_user_policy(UserName=user.name, PolicyArn=policy.arn)
    err = exc.value.response["Error"]
    assert err["Code"] == "NoSuchEntity"
    assert err["Message"] == f"Policy {policy.arn} was not found."


@mock_iam()
def test_only_detach_group_policy():
    iam = boto3.resource("iam", region_name="us-east-1")
    client = boto3.client("iam", region_name="us-east-1")

    group = iam.create_group(GroupName="test-group")

    policy_name = "FreePolicy"
    policy = iam.create_policy(
        PolicyName=policy_name,
        PolicyDocument=MOCK_POLICY,
        Path="/mypolicy/",
        Description="free floating policy",
    )

    resp = client.list_attached_group_policies(GroupName=group.name)
    assert len(resp["AttachedPolicies"]) == 0

    with pytest.raises(ClientError) as exc:
        client.detach_group_policy(GroupName=group.name, PolicyArn=policy.arn)
    err = exc.value.response["Error"]
    assert err["Code"] == "NoSuchEntity"
    assert err["Message"] == f"Policy {policy.arn} was not found."


@mock_iam()
def test_only_detach_role_policy():
    iam = boto3.resource("iam", region_name="us-east-1")
    client = boto3.client("iam", region_name="us-east-1")

    role = iam.create_role(RoleName="test-role", AssumeRolePolicyDocument="{}")

    policy_name = "FreePolicy"
    policy = iam.create_policy(
        PolicyName=policy_name,
        PolicyDocument=MOCK_POLICY,
        Path="/mypolicy/",
        Description="free floating policy",
    )

    resp = client.list_attached_role_policies(RoleName=role.name)
    assert len(resp["AttachedPolicies"]) == 0

    with pytest.raises(ClientError) as exc:
        client.detach_role_policy(RoleName=role.name, PolicyArn=policy.arn)
    err = exc.value.response["Error"]
    assert err["Code"] == "NoSuchEntity"
    assert err["Message"] == f"Policy {policy.arn} was not found."


@mock_iam
def test_update_access_key():
    iam = boto3.resource("iam", region_name="us-east-1")
    client = iam.meta.client
    username = "test-user"
    iam.create_user(UserName=username)
    with pytest.raises(ClientError):
        client.update_access_key(
            UserName=username, AccessKeyId="non-existent-key", Status="Inactive"
        )
    key = client.create_access_key(UserName=username)["AccessKey"]
    client.update_access_key(
        UserName=username, AccessKeyId=key["AccessKeyId"], Status="Inactive"
    )
    resp = client.list_access_keys(UserName=username)
    assert resp["AccessKeyMetadata"][0]["Status"] == "Inactive"
    client.update_access_key(AccessKeyId=key["AccessKeyId"], Status="Active")
    resp = client.list_access_keys(UserName=username)
    assert resp["AccessKeyMetadata"][0]["Status"] == "Active"


@mock_iam
def test_get_access_key_last_used_when_unused():
    iam = boto3.resource("iam", region_name="us-east-1")
    client = iam.meta.client
    username = "test-user"
    iam.create_user(UserName=username)
    with pytest.raises(ClientError):
        client.get_access_key_last_used(AccessKeyId="non-existent-key-id")
    create_key_response = client.create_access_key(UserName=username)["AccessKey"]
    resp = client.get_access_key_last_used(
        AccessKeyId=create_key_response["AccessKeyId"]
    )
    assert "LastUsedDate" not in resp["AccessKeyLastUsed"]
    assert resp["UserName"] == create_key_response["UserName"]


@mock_iam
def test_upload_ssh_public_key():
    iam = boto3.resource("iam", region_name="us-east-1")
    client = iam.meta.client
    username = "test-user"
    iam.create_user(UserName=username)
    public_key = MOCK_CERT

    resp = client.upload_ssh_public_key(UserName=username, SSHPublicKeyBody=public_key)
    pubkey = resp["SSHPublicKey"]
    assert pubkey["SSHPublicKeyBody"] == public_key
    assert pubkey["UserName"] == username
    assert len(pubkey["SSHPublicKeyId"]) == 20
    assert pubkey["SSHPublicKeyId"].startswith("APKA")
    assert "Fingerprint" in pubkey
    assert pubkey["Status"] == "Active"
    assert 0 <= ((utcnow() - pubkey["UploadDate"].replace(tzinfo=None)).seconds) < 10


@mock_iam
def test_get_ssh_public_key():
    iam = boto3.resource("iam", region_name="us-east-1")
    client = iam.meta.client
    username = "test-user"
    iam.create_user(UserName=username)
    public_key = MOCK_CERT

    with pytest.raises(ClientError):
        client.get_ssh_public_key(
            UserName=username, SSHPublicKeyId="xxnon-existent-keyxx", Encoding="SSH"
        )

    resp = client.upload_ssh_public_key(UserName=username, SSHPublicKeyBody=public_key)
    ssh_public_key_id = resp["SSHPublicKey"]["SSHPublicKeyId"]

    resp = client.get_ssh_public_key(
        UserName=username, SSHPublicKeyId=ssh_public_key_id, Encoding="SSH"
    )
    assert resp["SSHPublicKey"]["SSHPublicKeyBody"] == public_key


@mock_iam
def test_list_ssh_public_keys():
    iam = boto3.resource("iam", region_name="us-east-1")
    client = iam.meta.client
    username = "test-user"
    iam.create_user(UserName=username)
    public_key = MOCK_CERT

    resp = client.list_ssh_public_keys(UserName=username)
    assert len(resp["SSHPublicKeys"]) == 0

    resp = client.upload_ssh_public_key(UserName=username, SSHPublicKeyBody=public_key)
    ssh_public_key_id = resp["SSHPublicKey"]["SSHPublicKeyId"]

    resp = client.list_ssh_public_keys(UserName=username)
    assert len(resp["SSHPublicKeys"]) == 1
    assert resp["SSHPublicKeys"][0]["SSHPublicKeyId"] == ssh_public_key_id


@mock_iam
def test_update_ssh_public_key():
    iam = boto3.resource("iam", region_name="us-east-1")
    client = iam.meta.client
    username = "test-user"
    iam.create_user(UserName=username)
    public_key = MOCK_CERT

    with pytest.raises(ClientError):
        client.update_ssh_public_key(
            UserName=username, SSHPublicKeyId="xxnon-existent-keyxx", Status="Inactive"
        )

    resp = client.upload_ssh_public_key(UserName=username, SSHPublicKeyBody=public_key)
    ssh_public_key_id = resp["SSHPublicKey"]["SSHPublicKeyId"]
    assert resp["SSHPublicKey"]["Status"] == "Active"

    resp = client.update_ssh_public_key(
        UserName=username, SSHPublicKeyId=ssh_public_key_id, Status="Inactive"
    )

    resp = client.get_ssh_public_key(
        UserName=username, SSHPublicKeyId=ssh_public_key_id, Encoding="SSH"
    )
    assert resp["SSHPublicKey"]["Status"] == "Inactive"


@mock_iam
def test_delete_ssh_public_key():
    iam = boto3.resource("iam", region_name="us-east-1")
    client = iam.meta.client
    username = "test-user"
    iam.create_user(UserName=username)
    public_key = MOCK_CERT

    with pytest.raises(ClientError):
        client.delete_ssh_public_key(
            UserName=username, SSHPublicKeyId="xxnon-existent-keyxx"
        )

    resp = client.upload_ssh_public_key(UserName=username, SSHPublicKeyBody=public_key)
    ssh_public_key_id = resp["SSHPublicKey"]["SSHPublicKeyId"]

    resp = client.list_ssh_public_keys(UserName=username)
    assert len(resp["SSHPublicKeys"]) == 1

    resp = client.delete_ssh_public_key(
        UserName=username, SSHPublicKeyId=ssh_public_key_id
    )

    resp = client.list_ssh_public_keys(UserName=username)
    assert len(resp["SSHPublicKeys"]) == 0


@mock_iam
def test_get_account_authorization_details():
    test_policy = json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {"Action": "s3:ListBucket", "Resource": "*", "Effect": "Allow"}
            ],
        }
    )

    conn = boto3.client("iam", region_name="us-east-1")
    boundary = f"arn:aws:iam::{ACCOUNT_ID}:policy/boundary"
    conn.create_role(
        RoleName="my-role",
        AssumeRolePolicyDocument="some policy",
        Path="/my-path/",
        Description="testing",
        PermissionsBoundary=boundary,
    )
    conn.create_user(Path="/", UserName="testUser")
    conn.create_group(Path="/", GroupName="testGroup")
    conn.create_policy(
        PolicyName="testPolicy",
        Path="/",
        PolicyDocument=test_policy,
        Description="Test Policy",
    )

    # Attach things to the user and group:
    conn.put_user_policy(
        UserName="testUser", PolicyName="testPolicy", PolicyDocument=test_policy
    )
    conn.put_group_policy(
        GroupName="testGroup", PolicyName="testPolicy", PolicyDocument=test_policy
    )

    conn.attach_user_policy(
        UserName="testUser",
        PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/testPolicy",
    )
    conn.attach_group_policy(
        GroupName="testGroup",
        PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/testPolicy",
    )

    conn.add_user_to_group(UserName="testUser", GroupName="testGroup")

    # Add things to the role:
    conn.create_instance_profile(InstanceProfileName="ipn")
    conn.add_role_to_instance_profile(InstanceProfileName="ipn", RoleName="my-role")
    conn.tag_role(
        RoleName="my-role",
        Tags=[
            {"Key": "somekey", "Value": "somevalue"},
            {"Key": "someotherkey", "Value": "someothervalue"},
        ],
    )
    conn.put_role_policy(
        RoleName="my-role", PolicyName="test-policy", PolicyDocument=test_policy
    )
    conn.attach_role_policy(
        RoleName="my-role",
        PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/testPolicy",
    )
    # add tags to the user
    conn.tag_user(
        UserName="testUser",
        Tags=[
            {"Key": "somekey", "Value": "somevalue"},
            {"Key": "someotherkey", "Value": "someothervalue"},
        ],
    )

    result = conn.get_account_authorization_details(Filter=["Role"])
    assert len(result["RoleDetailList"]) == 1
    assert len(result["UserDetailList"]) == 0
    assert len(result["GroupDetailList"]) == 0
    assert len(result["Policies"]) == 0
    assert len(result["RoleDetailList"][0]["InstanceProfileList"]) == 1
    assert (
        result["RoleDetailList"][0]["InstanceProfileList"][0]["Roles"][0]["Description"]
        == "testing"
    )
    assert result["RoleDetailList"][0]["InstanceProfileList"][0]["Roles"][0][
        "PermissionsBoundary"
    ] == {
        "PermissionsBoundaryType": "PermissionsBoundaryPolicy",
        "PermissionsBoundaryArn": f"arn:aws:iam::{ACCOUNT_ID}:policy/boundary",
    }
    assert len(result["RoleDetailList"][0]["Tags"]) == 2
    assert len(result["RoleDetailList"][0]["RolePolicyList"]) == 1
    assert len(result["RoleDetailList"][0]["AttachedManagedPolicies"]) == 1
    assert (
        result["RoleDetailList"][0]["AttachedManagedPolicies"][0]["PolicyName"]
        == "testPolicy"
    )
    assert (
        result["RoleDetailList"][0]["AttachedManagedPolicies"][0]["PolicyArn"]
        == f"arn:aws:iam::{ACCOUNT_ID}:policy/testPolicy"
    )
    assert result["RoleDetailList"][0]["RolePolicyList"][0][
        "PolicyDocument"
    ] == json.loads(test_policy)

    result = conn.get_account_authorization_details(Filter=["User"])
    assert len(result["RoleDetailList"]) == 0
    assert len(result["UserDetailList"]) == 1
    assert len(result["UserDetailList"][0]["GroupList"]) == 1
    assert len(result["UserDetailList"][0]["UserPolicyList"]) == 1
    assert len(result["UserDetailList"][0]["AttachedManagedPolicies"]) == 1
    assert len(result["UserDetailList"][0]["Tags"]) == 2
    assert len(result["GroupDetailList"]) == 0
    assert len(result["Policies"]) == 0
    assert (
        result["UserDetailList"][0]["AttachedManagedPolicies"][0]["PolicyName"]
        == "testPolicy"
    )
    assert (
        result["UserDetailList"][0]["AttachedManagedPolicies"][0]["PolicyArn"]
        == f"arn:aws:iam::{ACCOUNT_ID}:policy/testPolicy"
    )
    assert result["UserDetailList"][0]["UserPolicyList"][0][
        "PolicyDocument"
    ] == json.loads(test_policy)

    result = conn.get_account_authorization_details(Filter=["Group"])
    assert len(result["RoleDetailList"]) == 0
    assert len(result["UserDetailList"]) == 0
    assert len(result["GroupDetailList"]) == 1
    assert len(result["GroupDetailList"][0]["GroupPolicyList"]) == 1
    assert len(result["GroupDetailList"][0]["AttachedManagedPolicies"]) == 1
    assert len(result["Policies"]) == 0
    assert (
        result["GroupDetailList"][0]["AttachedManagedPolicies"][0]["PolicyName"]
        == "testPolicy"
    )
    assert (
        result["GroupDetailList"][0]["AttachedManagedPolicies"][0]["PolicyArn"]
        == f"arn:aws:iam::{ACCOUNT_ID}:policy/testPolicy"
    )
    assert result["GroupDetailList"][0]["GroupPolicyList"][0][
        "PolicyDocument"
    ] == json.loads(test_policy)

    result = conn.get_account_authorization_details(Filter=["LocalManagedPolicy"])
    assert len(result["RoleDetailList"]) == 0
    assert len(result["UserDetailList"]) == 0
    assert len(result["GroupDetailList"]) == 0
    assert len(result["Policies"]) == 1
    assert len(result["Policies"][0]["PolicyVersionList"]) == 1

    # Check for greater than 1 since this should always be greater than one but might change.
    # See iam/aws_managed_policies.py
    result = conn.get_account_authorization_details(Filter=["AWSManagedPolicy"])
    assert len(result["RoleDetailList"]) == 0
    assert len(result["UserDetailList"]) == 0
    assert len(result["GroupDetailList"]) == 0
    assert len(result["Policies"]) > 1

    result = conn.get_account_authorization_details()
    assert len(result["RoleDetailList"]) == 1
    assert len(result["UserDetailList"]) == 1
    assert len(result["GroupDetailList"]) == 1
    assert len(result["Policies"]) > 1


@mock_iam
def test_signing_certs():
    client = boto3.client("iam", region_name="us-east-1")

    # Create the IAM user first:
    client.create_user(UserName="testing")

    # Upload the cert:
    resp = client.upload_signing_certificate(
        UserName="testing", CertificateBody=MOCK_CERT
    )["Certificate"]
    cert_id = resp["CertificateId"]

    assert resp["UserName"] == "testing"
    assert resp["Status"] == "Active"
    assert resp["CertificateBody"] == MOCK_CERT
    assert resp["CertificateId"]

    # Upload a the cert with an invalid body:
    with pytest.raises(ClientError) as ce:
        client.upload_signing_certificate(
            UserName="testing", CertificateBody="notacert"
        )
    assert ce.value.response["Error"]["Code"] == "MalformedCertificate"

    # Upload with an invalid user:
    with pytest.raises(ClientError):
        client.upload_signing_certificate(
            UserName="notauser", CertificateBody=MOCK_CERT
        )

    # Update:
    client.update_signing_certificate(
        UserName="testing", CertificateId=cert_id, Status="Inactive"
    )

    with pytest.raises(ClientError):
        client.update_signing_certificate(
            UserName="notauser", CertificateId=cert_id, Status="Inactive"
        )

    fake_id_name = "x" * 32
    with pytest.raises(ClientError) as ce:
        client.update_signing_certificate(
            UserName="testing", CertificateId=fake_id_name, Status="Inactive"
        )

    assert (
        ce.value.response["Error"]["Message"]
        == f"The Certificate with id {fake_id_name} cannot be found."
    )

    # List the certs:
    resp = client.list_signing_certificates(UserName="testing")["Certificates"]
    assert len(resp) == 1
    assert resp[0]["CertificateBody"] == MOCK_CERT
    assert resp[0]["Status"] == "Inactive"  # Changed with the update call above.

    with pytest.raises(ClientError):
        client.list_signing_certificates(UserName="notauser")

    # Delete:
    client.delete_signing_certificate(UserName="testing", CertificateId=cert_id)

    with pytest.raises(ClientError):
        client.delete_signing_certificate(UserName="notauser", CertificateId=cert_id)


@mock_iam()
def test_create_saml_provider():
    conn = boto3.client("iam", region_name="us-east-1")
    response = conn.create_saml_provider(
        Name="TestSAMLProvider", SAMLMetadataDocument="a" * 1024
    )
    assert (
        response["SAMLProviderArn"]
        == f"arn:aws:iam::{ACCOUNT_ID}:saml-provider/TestSAMLProvider"
    )


@mock_iam()
def test_get_saml_provider():
    conn = boto3.client("iam", region_name="us-east-1")
    saml_provider_create = conn.create_saml_provider(
        Name="TestSAMLProvider", SAMLMetadataDocument="a" * 1024
    )
    response = conn.get_saml_provider(
        SAMLProviderArn=saml_provider_create["SAMLProviderArn"]
    )
    assert response["SAMLMetadataDocument"] == "a" * 1024


@mock_iam()
def test_list_saml_providers():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_saml_provider(Name="TestSAMLProvider", SAMLMetadataDocument="a" * 1024)
    response = conn.list_saml_providers()
    assert (
        response["SAMLProviderList"][0]["Arn"]
        == f"arn:aws:iam::{ACCOUNT_ID}:saml-provider/TestSAMLProvider"
    )


@mock_iam()
def test_delete_saml_provider():
    conn = boto3.client("iam", region_name="us-east-1")
    saml_provider_create = conn.create_saml_provider(
        Name="TestSAMLProvider", SAMLMetadataDocument="a" * 1024
    )
    response = conn.list_saml_providers()
    assert len(response["SAMLProviderList"]) == 1
    conn.delete_saml_provider(SAMLProviderArn=saml_provider_create["SAMLProviderArn"])
    response = conn.list_saml_providers()
    assert len(response["SAMLProviderList"]) == 0
    conn.create_user(UserName="testing")

    cert_id = "123456789012345678901234"
    with pytest.raises(ClientError) as ce:
        conn.delete_signing_certificate(UserName="testing", CertificateId=cert_id)

    assert (
        ce.value.response["Error"]["Message"]
        == f"The Certificate with id {cert_id} cannot be found."
    )

    # Verify that it's not in the list:
    resp = conn.list_signing_certificates(UserName="testing")
    assert not resp["Certificates"]


@mock_iam()
def test_create_role_defaults():
    """Tests default values"""
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_role(RoleName="my-role", AssumeRolePolicyDocument="{}")

    # Get role:
    role = conn.get_role(RoleName="my-role")["Role"]
    assert role["RoleId"].startswith("AROA")
    assert role["MaxSessionDuration"] == 3600
    assert role.get("Description") is None


@mock_iam()
def test_create_role_with_tags():
    """Tests both the tag_role and get_role_tags capability"""
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_role(
        RoleName="my-role",
        AssumeRolePolicyDocument="{}",
        Tags=[
            {"Key": "somekey", "Value": "somevalue"},
            {"Key": "someotherkey", "Value": "someothervalue"},
        ],
        Description="testing",
    )

    # Get role:
    role = conn.get_role(RoleName="my-role")["Role"]
    assert len(role["Tags"]) == 2
    assert role["Tags"][0]["Key"] == "somekey"
    assert role["Tags"][0]["Value"] == "somevalue"
    assert role["Tags"][1]["Key"] == "someotherkey"
    assert role["Tags"][1]["Value"] == "someothervalue"
    assert role["Description"] == "testing"

    # Empty is good:
    conn.create_role(
        RoleName="my-role2",
        AssumeRolePolicyDocument="{}",
        Tags=[{"Key": "somekey", "Value": ""}],
    )
    tags = conn.list_role_tags(RoleName="my-role2")
    assert len(tags["Tags"]) == 1
    assert tags["Tags"][0]["Key"] == "somekey"
    assert tags["Tags"][0]["Value"] == ""

    # Test creating tags with invalid values:
    # With more than 50 tags:
    with pytest.raises(ClientError) as ce:
        too_many_tags = list(
            map(lambda x: {"Key": str(x), "Value": str(x)}, range(0, 51))
        )
        conn.create_role(
            RoleName="my-role3", AssumeRolePolicyDocument="{}", Tags=too_many_tags
        )
    assert (
        "failed to satisfy constraint: Member must have length less than or equal to 50."
        in ce.value.response["Error"]["Message"]
    )

    # With a duplicate tag:
    with pytest.raises(ClientError) as ce:
        conn.create_role(
            RoleName="my-role3",
            AssumeRolePolicyDocument="{}",
            Tags=[{"Key": "0", "Value": ""}, {"Key": "0", "Value": ""}],
        )
    assert (
        "Duplicate tag keys found. Please note that Tag keys are case insensitive."
        in ce.value.response["Error"]["Message"]
    )

    # Duplicate tag with different casing:
    with pytest.raises(ClientError) as ce:
        conn.create_role(
            RoleName="my-role3",
            AssumeRolePolicyDocument="{}",
            Tags=[{"Key": "a", "Value": ""}, {"Key": "A", "Value": ""}],
        )
    assert (
        "Duplicate tag keys found. Please note that Tag keys are case insensitive."
        in ce.value.response["Error"]["Message"]
    )

    # With a really big key:
    with pytest.raises(ClientError) as ce:
        conn.create_role(
            RoleName="my-role3",
            AssumeRolePolicyDocument="{}",
            Tags=[{"Key": "0" * 129, "Value": ""}],
        )
    assert (
        "Member must have length less than or equal to 128."
        in ce.value.response["Error"]["Message"]
    )

    # With a really big value:
    with pytest.raises(ClientError) as ce:
        conn.create_role(
            RoleName="my-role3",
            AssumeRolePolicyDocument="{}",
            Tags=[{"Key": "0", "Value": "0" * 257}],
        )
    assert (
        "Member must have length less than or equal to 256."
        in ce.value.response["Error"]["Message"]
    )

    # With an invalid character:
    with pytest.raises(ClientError) as ce:
        conn.create_role(
            RoleName="my-role3",
            AssumeRolePolicyDocument="{}",
            Tags=[{"Key": "NOWAY!", "Value": ""}],
        )
    assert (
        "Member must satisfy regular expression pattern: [\\p{L}\\p{Z}\\p{N}_.:/=+\\-@]+"
        in ce.value.response["Error"]["Message"]
    )


@mock_iam()
def test_tag_role():
    """Tests both the tag_role and get_role_tags capability"""
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_role(RoleName="my-role", AssumeRolePolicyDocument="{}")

    # Get without tags:
    role = conn.get_role(RoleName="my-role")["Role"]
    assert not role.get("Tags")

    # With proper tag values:
    conn.tag_role(
        RoleName="my-role",
        Tags=[
            {"Key": "somekey", "Value": "somevalue"},
            {"Key": "someotherkey", "Value": "someothervalue"},
        ],
    )

    # Get role:
    role = conn.get_role(RoleName="my-role")["Role"]
    assert len(role["Tags"]) == 2
    assert role["Tags"][0]["Key"] == "somekey"
    assert role["Tags"][0]["Value"] == "somevalue"
    assert role["Tags"][1]["Key"] == "someotherkey"
    assert role["Tags"][1]["Value"] == "someothervalue"

    # Same -- but for list_role_tags:
    tags = conn.list_role_tags(RoleName="my-role")
    assert len(tags["Tags"]) == 2
    assert role["Tags"][0]["Key"] == "somekey"
    assert role["Tags"][0]["Value"] == "somevalue"
    assert role["Tags"][1]["Key"] == "someotherkey"
    assert role["Tags"][1]["Value"] == "someothervalue"
    assert not tags["IsTruncated"]
    assert not tags.get("Marker")

    # Test pagination:
    tags = conn.list_role_tags(RoleName="my-role", MaxItems=1)
    assert len(tags["Tags"]) == 1
    assert tags["IsTruncated"]
    assert tags["Tags"][0]["Key"] == "somekey"
    assert tags["Tags"][0]["Value"] == "somevalue"
    assert tags["Marker"] == "1"

    tags = conn.list_role_tags(RoleName="my-role", Marker=tags["Marker"])
    assert len(tags["Tags"]) == 1
    assert tags["Tags"][0]["Key"] == "someotherkey"
    assert tags["Tags"][0]["Value"] == "someothervalue"
    assert not tags["IsTruncated"]
    assert not tags.get("Marker")

    # Test updating an existing tag:
    conn.tag_role(
        RoleName="my-role", Tags=[{"Key": "somekey", "Value": "somenewvalue"}]
    )
    tags = conn.list_role_tags(RoleName="my-role")
    assert len(tags["Tags"]) == 2
    assert tags["Tags"][0]["Key"] == "somekey"
    assert tags["Tags"][0]["Value"] == "somenewvalue"

    # Empty is good:
    conn.tag_role(RoleName="my-role", Tags=[{"Key": "somekey", "Value": ""}])
    tags = conn.list_role_tags(RoleName="my-role")
    assert len(tags["Tags"]) == 2
    assert tags["Tags"][0]["Key"] == "somekey"
    assert tags["Tags"][0]["Value"] == ""

    # Test creating tags with invalid values:
    # With more than 50 tags:
    with pytest.raises(ClientError) as ce:
        too_many_tags = list(
            map(lambda x: {"Key": str(x), "Value": str(x)}, range(0, 51))
        )
        conn.tag_role(RoleName="my-role", Tags=too_many_tags)
    assert (
        "failed to satisfy constraint: Member must have length less than or equal to 50."
        in ce.value.response["Error"]["Message"]
    )

    # With a duplicate tag:
    with pytest.raises(ClientError) as ce:
        conn.tag_role(
            RoleName="my-role",
            Tags=[{"Key": "0", "Value": ""}, {"Key": "0", "Value": ""}],
        )
    assert (
        "Duplicate tag keys found. Please note that Tag keys are case insensitive."
        in ce.value.response["Error"]["Message"]
    )

    # Duplicate tag with different casing:
    with pytest.raises(ClientError) as ce:
        conn.tag_role(
            RoleName="my-role",
            Tags=[{"Key": "a", "Value": ""}, {"Key": "A", "Value": ""}],
        )
    assert (
        "Duplicate tag keys found. Please note that Tag keys are case insensitive."
        in ce.value.response["Error"]["Message"]
    )

    # With a really big key:
    with pytest.raises(ClientError) as ce:
        conn.tag_role(RoleName="my-role", Tags=[{"Key": "0" * 129, "Value": ""}])
    assert (
        "Member must have length less than or equal to 128."
        in ce.value.response["Error"]["Message"]
    )

    # With a really big value:
    with pytest.raises(ClientError) as ce:
        conn.tag_role(RoleName="my-role", Tags=[{"Key": "0", "Value": "0" * 257}])
    assert (
        "Member must have length less than or equal to 256."
        in ce.value.response["Error"]["Message"]
    )

    # With an invalid character:
    with pytest.raises(ClientError) as ce:
        conn.tag_role(RoleName="my-role", Tags=[{"Key": "NOWAY!", "Value": ""}])
    assert (
        "Member must satisfy regular expression pattern: [\\p{L}\\p{Z}\\p{N}_.:/=+\\-@]+"
        in ce.value.response["Error"]["Message"]
    )

    # With a role that doesn't exist:
    with pytest.raises(ClientError):
        conn.tag_role(RoleName="notarole", Tags=[{"Key": "some", "Value": "value"}])


@mock_iam
def test_untag_role():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_role(RoleName="my-role", AssumeRolePolicyDocument="{}")

    # With proper tag values:
    conn.tag_role(
        RoleName="my-role",
        Tags=[
            {"Key": "somekey", "Value": "somevalue"},
            {"Key": "someotherkey", "Value": "someothervalue"},
        ],
    )

    # Remove them:
    conn.untag_role(RoleName="my-role", TagKeys=["somekey"])
    tags = conn.list_role_tags(RoleName="my-role")
    assert len(tags["Tags"]) == 1
    assert tags["Tags"][0]["Key"] == "someotherkey"
    assert tags["Tags"][0]["Value"] == "someothervalue"

    # And again:
    conn.untag_role(RoleName="my-role", TagKeys=["someotherkey"])
    tags = conn.list_role_tags(RoleName="my-role")
    assert not tags["Tags"]

    # Test removing tags with invalid values:
    # With more than 50 tags:
    with pytest.raises(ClientError) as ce:
        conn.untag_role(RoleName="my-role", TagKeys=[str(x) for x in range(0, 51)])
    assert (
        "failed to satisfy constraint: Member must have length less than or equal to 50."
        in ce.value.response["Error"]["Message"]
    )
    assert "tagKeys" in ce.value.response["Error"]["Message"]

    # With a really big key:
    with pytest.raises(ClientError) as ce:
        conn.untag_role(RoleName="my-role", TagKeys=["0" * 129])
    assert (
        "Member must have length less than or equal to 128."
        in ce.value.response["Error"]["Message"]
    )
    assert "tagKeys" in ce.value.response["Error"]["Message"]

    # With an invalid character:
    with pytest.raises(ClientError) as ce:
        conn.untag_role(RoleName="my-role", TagKeys=["NOWAY!"])
    assert (
        "Member must satisfy regular expression pattern: [\\p{L}\\p{Z}\\p{N}_.:/=+\\-@]+"
        in ce.value.response["Error"]["Message"]
    )
    assert "tagKeys" in ce.value.response["Error"]["Message"]

    # With a role that doesn't exist:
    with pytest.raises(ClientError):
        conn.untag_role(RoleName="notarole", TagKeys=["somevalue"])


@mock_iam()
def test_update_role_description():
    conn = boto3.client("iam", region_name="us-east-1")

    with pytest.raises(ClientError):
        conn.delete_role(RoleName="my-role")

    conn.create_role(
        RoleName="my-role", AssumeRolePolicyDocument="some policy", Path="/my-path/"
    )
    response = conn.update_role_description(RoleName="my-role", Description="test")

    assert response["Role"]["RoleName"] == "my-role"


@mock_iam()
def test_update_role():
    conn = boto3.client("iam", region_name="us-east-1")

    with pytest.raises(ClientError):
        conn.delete_role(RoleName="my-role")

    conn.create_role(
        RoleName="my-role", AssumeRolePolicyDocument="some policy", Path="/my-path/"
    )
    response = conn.update_role(RoleName="my-role", Description="test")
    assert len(response.keys()) == 1


@mock_iam()
def test_update_role_defaults():
    conn = boto3.client("iam", region_name="us-east-1")

    with pytest.raises(ClientError):
        conn.delete_role(RoleName="my-role")

    conn.create_role(
        RoleName="my-role",
        AssumeRolePolicyDocument="some policy",
        Description="test",
        Path="/my-path/",
    )
    response = conn.update_role(RoleName="my-role")
    assert len(response.keys()) == 1

    role = conn.get_role(RoleName="my-role")["Role"]

    assert role["MaxSessionDuration"] == 3600
    assert role.get("Description") is None


@mock_iam()
def test_list_entities_for_policy():
    test_policy = json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {"Action": "s3:ListBucket", "Resource": "*", "Effect": "Allow"}
            ],
        }
    )

    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_role(
        RoleName="my-role", AssumeRolePolicyDocument="some policy", Path="/my-path/"
    )
    conn.create_user(Path="/", UserName="testUser")
    conn.create_group(Path="/", GroupName="testGroup")
    conn.create_policy(
        PolicyName="testPolicy",
        Path="/",
        PolicyDocument=test_policy,
        Description="Test Policy",
    )

    # Attach things to the user and group:
    conn.put_user_policy(
        UserName="testUser", PolicyName="testPolicy", PolicyDocument=test_policy
    )
    conn.put_group_policy(
        GroupName="testGroup", PolicyName="testPolicy", PolicyDocument=test_policy
    )

    conn.attach_user_policy(
        UserName="testUser",
        PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/testPolicy",
    )
    conn.attach_group_policy(
        GroupName="testGroup",
        PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/testPolicy",
    )

    conn.add_user_to_group(UserName="testUser", GroupName="testGroup")

    # Add things to the role:
    conn.create_instance_profile(InstanceProfileName="ipn")
    conn.add_role_to_instance_profile(InstanceProfileName="ipn", RoleName="my-role")
    conn.tag_role(
        RoleName="my-role",
        Tags=[
            {"Key": "somekey", "Value": "somevalue"},
            {"Key": "someotherkey", "Value": "someothervalue"},
        ],
    )
    conn.put_role_policy(
        RoleName="my-role", PolicyName="test-policy", PolicyDocument=test_policy
    )
    conn.attach_role_policy(
        RoleName="my-role",
        PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/testPolicy",
    )

    response = conn.list_entities_for_policy(
        PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/testPolicy",
        EntityFilter="Role",
    )
    assert response["PolicyRoles"][0]["RoleName"] == "my-role"
    assert "RoleId" in response["PolicyRoles"][0]
    assert response["PolicyGroups"] == []
    assert response["PolicyUsers"] == []

    response = conn.list_entities_for_policy(
        PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/testPolicy",
        EntityFilter="User",
    )
    assert response["PolicyUsers"][0]["UserName"] == "testUser"
    assert "UserId" in response["PolicyUsers"][0]
    assert response["PolicyGroups"] == []
    assert response["PolicyRoles"] == []

    response = conn.list_entities_for_policy(
        PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/testPolicy",
        EntityFilter="Group",
    )
    assert response["PolicyGroups"][0]["GroupName"] == "testGroup"
    assert "GroupId" in response["PolicyGroups"][0]
    assert response["PolicyRoles"] == []
    assert response["PolicyUsers"] == []

    response = conn.list_entities_for_policy(
        PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/testPolicy",
        EntityFilter="LocalManagedPolicy",
    )
    assert response["PolicyGroups"][0]["GroupName"] == "testGroup"
    assert response["PolicyUsers"][0]["UserName"] == "testUser"
    assert response["PolicyRoles"][0]["RoleName"] == "my-role"

    assert "GroupId" in response["PolicyGroups"][0]
    assert "UserId" in response["PolicyUsers"][0]
    assert "RoleId" in response["PolicyRoles"][0]

    # Return everything when no entity is specified
    response = conn.list_entities_for_policy(
        PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/testPolicy"
    )
    assert response["PolicyGroups"][0]["GroupName"] == "testGroup"
    assert response["PolicyUsers"][0]["UserName"] == "testUser"
    assert response["PolicyRoles"][0]["RoleName"] == "my-role"

    assert "GroupId" in response["PolicyGroups"][0]
    assert "UserId" in response["PolicyUsers"][0]
    assert "RoleId" in response["PolicyRoles"][0]


@mock_iam()
def test_create_role_no_path():
    conn = boto3.client("iam", region_name="us-east-1")
    resp = conn.create_role(
        RoleName="my-role", AssumeRolePolicyDocument="some policy", Description="test"
    )
    assert resp["Role"].get("Arn") == f"arn:aws:iam::{ACCOUNT_ID}:role/my-role"
    assert "PermissionsBoundary" not in resp["Role"]
    assert resp["Role"]["Description"] == "test"


@mock_iam()
def test_create_role_with_permissions_boundary():
    conn = boto3.client("iam", region_name="us-east-1")
    boundary = f"arn:aws:iam::{ACCOUNT_ID}:policy/boundary"
    resp = conn.create_role(
        RoleName="my-role",
        AssumeRolePolicyDocument="some policy",
        Description="test",
        PermissionsBoundary=boundary,
    )
    expected = {
        "PermissionsBoundaryType": "PermissionsBoundaryPolicy",
        "PermissionsBoundaryArn": boundary,
    }
    assert resp["Role"].get("PermissionsBoundary") == expected
    assert resp["Role"]["Description"] == "test"

    conn.delete_role_permissions_boundary(RoleName="my-role")
    assert "PermissionsBoundary" not in conn.list_roles()["Roles"][0]

    conn.put_role_permissions_boundary(RoleName="my-role", PermissionsBoundary=boundary)
    assert resp["Role"].get("PermissionsBoundary") == expected

    invalid_boundary_arn = "arn:aws:iam::123456789:not_a_boundary"

    with pytest.raises(ClientError):
        conn.put_role_permissions_boundary(
            RoleName="my-role", PermissionsBoundary=invalid_boundary_arn
        )

    with pytest.raises(ClientError):
        conn.create_role(
            RoleName="bad-boundary",
            AssumeRolePolicyDocument="some policy",
            Description="test",
            PermissionsBoundary=invalid_boundary_arn,
        )

    # Ensure the PermissionsBoundary is included in role listing as well
    assert conn.list_roles()["Roles"][0].get("PermissionsBoundary") == expected


@mock_iam
def test_create_role_with_same_name_should_fail():
    iam = boto3.client("iam", region_name="us-east-1")
    test_role_name = str(uuid4())
    iam.create_role(
        RoleName=test_role_name, AssumeRolePolicyDocument="policy", Description="test"
    )
    # Create the role again, and verify that it fails
    with pytest.raises(ClientError) as err:
        iam.create_role(
            RoleName=test_role_name,
            AssumeRolePolicyDocument="policy",
            Description="test",
        )
    assert err.value.response["Error"]["Code"] == "EntityAlreadyExists"
    assert (
        err.value.response["Error"]["Message"]
        == f"Role with name {test_role_name} already exists."
    )


@mock_iam
def test_create_policy_with_same_name_should_fail():
    iam = boto3.client("iam", region_name="us-east-1")
    test_policy_name = str(uuid4())
    iam.create_policy(PolicyName=test_policy_name, PolicyDocument=MOCK_POLICY)
    # Create the role again, and verify that it fails
    with pytest.raises(ClientError) as err:
        iam.create_policy(PolicyName=test_policy_name, PolicyDocument=MOCK_POLICY)
    assert err.value.response["Error"]["Code"] == "EntityAlreadyExists"
    assert (
        err.value.response["Error"]["Message"]
        == f"A policy called {test_policy_name} already exists. Duplicate names are not allowed."
    )


@mock_iam
def test_update_account_password_policy():
    client = boto3.client("iam", region_name="us-east-1")

    client.update_account_password_policy()

    response = client.get_account_password_policy()
    assert response["PasswordPolicy"] == {
        "AllowUsersToChangePassword": False,
        "ExpirePasswords": False,
        "MinimumPasswordLength": 6,
        "RequireLowercaseCharacters": False,
        "RequireNumbers": False,
        "RequireSymbols": False,
        "RequireUppercaseCharacters": False,
        "HardExpiry": False,
    }


@mock_iam
def test_update_account_password_policy_errors():
    client = boto3.client("iam", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        client.update_account_password_policy(
            MaxPasswordAge=1096, MinimumPasswordLength=129, PasswordReusePrevention=25
        )
    err = exc.value.response["Error"]
    assert (
        err["Message"]
        == '3 validation errors detected: Value "129" at "minimumPasswordLength" failed to satisfy constraint: Member must have value less than or equal to 128; Value "25" at "passwordReusePrevention" failed to satisfy constraint: Member must have value less than or equal to 24; Value "1096" at "maxPasswordAge" failed to satisfy constraint: Member must have value less than or equal to 1095'
    )


@mock_iam
def test_get_account_password_policy():
    client = boto3.client("iam", region_name="us-east-1")
    client.update_account_password_policy(
        AllowUsersToChangePassword=True,
        HardExpiry=True,
        MaxPasswordAge=60,
        MinimumPasswordLength=10,
        PasswordReusePrevention=3,
        RequireLowercaseCharacters=True,
        RequireNumbers=True,
        RequireSymbols=True,
        RequireUppercaseCharacters=True,
    )

    response = client.get_account_password_policy()

    assert response["PasswordPolicy"] == {
        "AllowUsersToChangePassword": True,
        "ExpirePasswords": True,
        "HardExpiry": True,
        "MaxPasswordAge": 60,
        "MinimumPasswordLength": 10,
        "PasswordReusePrevention": 3,
        "RequireLowercaseCharacters": True,
        "RequireNumbers": True,
        "RequireSymbols": True,
        "RequireUppercaseCharacters": True,
    }


@mock_iam
def test_get_account_password_policy_errors():
    client = boto3.client("iam", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        client.get_account_password_policy()
    err = exc.value.response["Error"]
    assert (
        err["Message"]
        == f"The Password Policy with domain name {ACCOUNT_ID} cannot be found."
    )


@mock_iam
def test_delete_account_password_policy():
    client = boto3.client("iam", region_name="us-east-1")
    client.update_account_password_policy()

    response = client.get_account_password_policy()

    assert isinstance(response["PasswordPolicy"], dict)

    client.delete_account_password_policy()

    with pytest.raises(ClientError) as exc:
        client.get_account_password_policy()
    err = exc.value.response["Error"]
    assert (
        err["Message"]
        == f"The Password Policy with domain name {ACCOUNT_ID} cannot be found."
    )


@mock_iam
def test_get_account_summary():
    client = boto3.client("iam", region_name="us-east-1")
    iam = boto3.resource("iam", region_name="us-east-1")

    account_summary = iam.AccountSummary()

    assert account_summary.summary_map == {
        "GroupPolicySizeQuota": 5120,
        "InstanceProfilesQuota": 1000,
        "Policies": 0,
        "GroupsPerUserQuota": 10,
        "InstanceProfiles": 0,
        "AttachedPoliciesPerUserQuota": 10,
        "Users": 0,
        "PoliciesQuota": 1500,
        "Providers": 0,
        "AccountMFAEnabled": 0,
        "AccessKeysPerUserQuota": 2,
        "AssumeRolePolicySizeQuota": 2048,
        "PolicyVersionsInUseQuota": 10000,
        "GlobalEndpointTokenVersion": 1,
        "VersionsPerPolicyQuota": 5,
        "AttachedPoliciesPerGroupQuota": 10,
        "PolicySizeQuota": 6144,
        "Groups": 0,
        "AccountSigningCertificatesPresent": 0,
        "UsersQuota": 5000,
        "ServerCertificatesQuota": 20,
        "MFADevices": 0,
        "UserPolicySizeQuota": 2048,
        "PolicyVersionsInUse": 0,
        "ServerCertificates": 0,
        "Roles": 0,
        "RolesQuota": 1000,
        "SigningCertificatesPerUserQuota": 2,
        "MFADevicesInUse": 0,
        "RolePolicySizeQuota": 10240,
        "AttachedPoliciesPerRoleQuota": 10,
        "AccountAccessKeysPresent": 0,
        "GroupsQuota": 300,
    }

    client.create_instance_profile(InstanceProfileName="test-profile")
    client.create_open_id_connect_provider(Url="https://example.com", ThumbprintList=[])
    response_policy = client.create_policy(
        PolicyName="test-policy", PolicyDocument=MOCK_POLICY
    )
    client.create_role(RoleName="test-role", AssumeRolePolicyDocument="test policy")
    client.attach_role_policy(
        RoleName="test-role", PolicyArn=response_policy["Policy"]["Arn"]
    )
    client.create_saml_provider(
        Name="TestSAMLProvider", SAMLMetadataDocument="a" * 1024
    )
    client.create_group(GroupName="test-group")
    client.attach_group_policy(
        GroupName="test-group", PolicyArn=response_policy["Policy"]["Arn"]
    )
    client.create_user(UserName="test-user")
    client.attach_user_policy(
        UserName="test-user", PolicyArn=response_policy["Policy"]["Arn"]
    )
    client.enable_mfa_device(
        UserName="test-user",
        SerialNumber="123456789",
        AuthenticationCode1="234567",
        AuthenticationCode2="987654",
    )
    client.create_virtual_mfa_device(VirtualMFADeviceName="test-device")
    client.upload_server_certificate(
        ServerCertificateName="test-cert",
        CertificateBody="cert-body",
        PrivateKey="private-key",
    )
    account_summary.load()

    assert account_summary.summary_map == {
        "GroupPolicySizeQuota": 5120,
        "InstanceProfilesQuota": 1000,
        "Policies": 1,
        "GroupsPerUserQuota": 10,
        "InstanceProfiles": 1,
        "AttachedPoliciesPerUserQuota": 10,
        "Users": 1,
        "PoliciesQuota": 1500,
        "Providers": 2,
        "AccountMFAEnabled": 0,
        "AccessKeysPerUserQuota": 2,
        "AssumeRolePolicySizeQuota": 2048,
        "PolicyVersionsInUseQuota": 10000,
        "GlobalEndpointTokenVersion": 1,
        "VersionsPerPolicyQuota": 5,
        "AttachedPoliciesPerGroupQuota": 10,
        "PolicySizeQuota": 6144,
        "Groups": 1,
        "AccountSigningCertificatesPresent": 0,
        "UsersQuota": 5000,
        "ServerCertificatesQuota": 20,
        "MFADevices": 1,
        "UserPolicySizeQuota": 2048,
        "PolicyVersionsInUse": 3,
        "ServerCertificates": 1,
        "Roles": 1,
        "RolesQuota": 1000,
        "SigningCertificatesPerUserQuota": 2,
        "MFADevicesInUse": 1,
        "RolePolicySizeQuota": 10240,
        "AttachedPoliciesPerRoleQuota": 10,
        "AccountAccessKeysPresent": 0,
        "GroupsQuota": 300,
    }


@mock_iam()
def test_list_user_tags():
    """Tests both setting a tags on a user in create_user and list_user_tags"""
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_user(UserName="kenny-bania")
    conn.create_user(
        UserName="jackie-chiles", Tags=[{"Key": "Sue-Allen", "Value": "Oh-Henry"}]
    )
    conn.create_user(
        UserName="cosmo",
        Tags=[
            {"Key": "Stan", "Value": "The Caddy"},
            {"Key": "like-a", "Value": "glove"},
        ],
    )
    response = conn.list_user_tags(UserName="kenny-bania")
    assert len(response["Tags"]) == 0
    assert response["IsTruncated"] is False

    response = conn.list_user_tags(UserName="jackie-chiles")
    assert response["Tags"] == [{"Key": "Sue-Allen", "Value": "Oh-Henry"}]
    assert response["IsTruncated"] is False

    response = conn.list_user_tags(UserName="cosmo")
    assert response["Tags"] == [
        {"Key": "Stan", "Value": "The Caddy"},
        {"Key": "like-a", "Value": "glove"},
    ]
    assert response["IsTruncated"] is False


@mock_iam()
def test_delete_role_with_instance_profiles_present():
    iam = boto3.client("iam", region_name="us-east-1")

    trust_policy = MOCK_STS_EC2_POLICY_DOCUMENT.strip()

    iam.create_role(RoleName="Role1", AssumeRolePolicyDocument=trust_policy)
    iam.create_instance_profile(InstanceProfileName="IP1")
    iam.add_role_to_instance_profile(InstanceProfileName="IP1", RoleName="Role1")

    iam.create_role(RoleName="Role2", AssumeRolePolicyDocument=trust_policy)

    iam.delete_role(RoleName="Role2")

    role_names = [role["RoleName"] for role in iam.list_roles()["Roles"]]
    assert "Role1" in role_names
    assert "Role2" not in role_names


@mock_iam
def test_delete_account_password_policy_errors():
    client = boto3.client("iam", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        client.delete_account_password_policy()
    err = exc.value.response["Error"]
    assert (
        err["Message"] == "The account policy with name PasswordPolicy cannot be found."
    )


@mock_iam
def test_role_list_config_discovered_resources():
    from moto.iam.config import role_config_query

    # Without any roles
    assert role_config_query.list_config_service_resources(
        DEFAULT_ACCOUNT_ID, None, None, 100, None
    ) == (
        [],
        None,
    )

    # Make 3 roles
    roles = []
    num_roles = 3
    for ix in range(1, num_roles + 1):
        this_role = role_config_query.backends[DEFAULT_ACCOUNT_ID][
            "global"
        ].create_role(
            role_name=f"role{ix}",
            assume_role_policy_document=None,
            path="/",
            permissions_boundary=None,
            description=f"role{ix}",
            tags=[{"Key": "foo", "Value": "bar"}],
            max_session_duration=3600,
        )
        roles.append({"id": this_role.id, "name": this_role.name})

    assert len(roles) == num_roles

    result = role_config_query.list_config_service_resources(
        DEFAULT_ACCOUNT_ID, None, None, 100, None
    )[0]
    assert len(result) == num_roles

    # The roles gets a random ID, so we can't directly test it
    role = result[0]
    assert role["type"] == "AWS::IAM::Role"
    assert role["id"] in list(map(lambda p: p["id"], roles))
    assert role["name"] in list(map(lambda p: p["name"], roles))
    assert role["region"] == "global"

    # test passing list of resource ids
    resource_ids = role_config_query.list_config_service_resources(
        DEFAULT_ACCOUNT_ID, [roles[0]["id"], roles[1]["id"]], None, 100, None
    )[0]
    assert len(resource_ids) == 2

    # test passing a single resource name
    resource_name = role_config_query.list_config_service_resources(
        DEFAULT_ACCOUNT_ID, None, roles[0]["name"], 100, None
    )[0]
    assert len(resource_name) == 1
    assert resource_name[0]["id"] == roles[0]["id"]
    assert resource_name[0]["name"] == roles[0]["name"]

    # test passing a single resource name AND some resource id's
    both_filter_good = role_config_query.list_config_service_resources(
        DEFAULT_ACCOUNT_ID,
        [roles[0]["id"], roles[1]["id"]],
        roles[0]["name"],
        100,
        None,
    )[0]
    assert len(both_filter_good) == 1
    assert both_filter_good[0]["id"] == roles[0]["id"]
    assert both_filter_good[0]["name"] == roles[0]["name"]

    both_filter_bad = role_config_query.list_config_service_resources(
        DEFAULT_ACCOUNT_ID,
        [roles[0]["id"], roles[1]["id"]],
        roles[2]["name"],
        100,
        None,
    )[0]
    assert len(both_filter_bad) == 0


@mock_iam
def test_role_config_dict():
    from moto.iam.config import role_config_query, policy_config_query
    from moto.iam.utils import random_role_id, random_policy_id

    # Without any roles
    assert not role_config_query.get_config_resource(DEFAULT_ACCOUNT_ID, "something")
    assert role_config_query.list_config_service_resources(
        DEFAULT_ACCOUNT_ID, None, None, 100, None
    ) == (
        [],
        None,
    )

    basic_assume_role = {
        "Version": "2012-10-17",
        "Statement": [
            {"Effect": "Allow", "Principal": {"AWS": "*"}, "Action": "sts:AssumeRole"}
        ],
    }

    basic_policy = {
        "Version": "2012-10-17",
        "Statement": [{"Action": ["ec2:*"], "Effect": "Allow", "Resource": "*"}],
    }

    # Create a policy for use in role permissions boundary
    policy_arn = (
        policy_config_query.backends[DEFAULT_ACCOUNT_ID]["global"]
        .create_policy(
            description="basic_policy",
            path="/",
            policy_document=json.dumps(basic_policy),
            policy_name="basic_policy",
            tags=[],
        )
        .arn
    )

    policy_id = policy_config_query.list_config_service_resources(
        DEFAULT_ACCOUNT_ID, None, None, 100, None
    )[0][0]["id"]
    assert len(policy_id) == len(random_policy_id())

    # Create some roles (and grab them repeatedly since they create with random names)
    role_config_query.backends[DEFAULT_ACCOUNT_ID]["global"].create_role(
        role_name="plain_role",
        assume_role_policy_document=None,
        path="/",
        permissions_boundary=None,
        description="plain_role",
        tags=[{"Key": "foo", "Value": "bar"}],
        max_session_duration=3600,
    )

    plain_role = role_config_query.list_config_service_resources(
        DEFAULT_ACCOUNT_ID, None, None, 100, None
    )[0][0]
    assert plain_role is not None
    assert len(plain_role["id"]) == len(random_role_id(DEFAULT_ACCOUNT_ID))

    role_config_query.backends[DEFAULT_ACCOUNT_ID]["global"].create_role(
        role_name="assume_role",
        assume_role_policy_document=json.dumps(basic_assume_role),
        path="/",
        permissions_boundary=None,
        description="assume_role",
        tags=[],
        max_session_duration=3600,
    )

    assume_role = next(
        role
        for role in role_config_query.list_config_service_resources(
            DEFAULT_ACCOUNT_ID, None, None, 100, None
        )[0]
        if role["id"] not in [plain_role["id"]]
    )
    assert assume_role is not None
    assert len(assume_role["id"]) == len(random_role_id(DEFAULT_ACCOUNT_ID))
    assert assume_role["id"] is not plain_role["id"]

    role_config_query.backends[DEFAULT_ACCOUNT_ID]["global"].create_role(
        role_name="assume_and_permission_boundary_role",
        assume_role_policy_document=json.dumps(basic_assume_role),
        path="/",
        permissions_boundary=policy_arn,
        description="assume_and_permission_boundary_role",
        tags=[],
        max_session_duration=3600,
    )

    assume_and_permission_boundary_role = next(
        role
        for role in role_config_query.list_config_service_resources(
            DEFAULT_ACCOUNT_ID, None, None, 100, None
        )[0]
        if role["id"] not in [plain_role["id"], assume_role["id"]]
    )
    assert assume_and_permission_boundary_role is not None
    assert len(assume_and_permission_boundary_role["id"]) == len(
        random_role_id(DEFAULT_ACCOUNT_ID)
    )
    assert assume_and_permission_boundary_role["id"] is not plain_role["id"]
    assert assume_and_permission_boundary_role["id"] is not assume_role["id"]

    role_config_query.backends[DEFAULT_ACCOUNT_ID]["global"].create_role(
        role_name="role_with_attached_policy",
        assume_role_policy_document=json.dumps(basic_assume_role),
        path="/",
        permissions_boundary=None,
        description="role_with_attached_policy",
        tags=[],
        max_session_duration=3600,
    )
    role_config_query.backends[DEFAULT_ACCOUNT_ID]["global"].attach_role_policy(
        policy_arn, "role_with_attached_policy"
    )
    role_with_attached_policy = next(
        role
        for role in role_config_query.list_config_service_resources(
            DEFAULT_ACCOUNT_ID, None, None, 100, None
        )[0]
        if role["id"]
        not in [
            plain_role["id"],
            assume_role["id"],
            assume_and_permission_boundary_role["id"],
        ]
    )
    assert role_with_attached_policy is not None
    assert len(role_with_attached_policy["id"]) == len(
        random_role_id(DEFAULT_ACCOUNT_ID)
    )
    assert role_with_attached_policy["id"] is not plain_role["id"]
    assert role_with_attached_policy["id"] is not assume_role["id"]
    assert (
        role_with_attached_policy["id"] is not assume_and_permission_boundary_role["id"]
    )

    role_config_query.backends[DEFAULT_ACCOUNT_ID]["global"].create_role(
        role_name="role_with_inline_policy",
        assume_role_policy_document=json.dumps(basic_assume_role),
        path="/",
        permissions_boundary=None,
        description="role_with_inline_policy",
        tags=[],
        max_session_duration=3600,
    )
    role_config_query.backends[DEFAULT_ACCOUNT_ID]["global"].put_role_policy(
        "role_with_inline_policy", "inline_policy", json.dumps(basic_policy)
    )

    role_with_inline_policy = next(
        role
        for role in role_config_query.list_config_service_resources(
            DEFAULT_ACCOUNT_ID, None, None, 100, None
        )[0]
        if role["id"]
        not in [
            plain_role["id"],
            assume_role["id"],
            assume_and_permission_boundary_role["id"],
            role_with_attached_policy["id"],
        ]
    )
    assert role_with_inline_policy is not None
    assert len(role_with_inline_policy["id"]) == len(random_role_id(DEFAULT_ACCOUNT_ID))
    assert role_with_inline_policy["id"] is not plain_role["id"]
    assert role_with_inline_policy["id"] is not assume_role["id"]
    assert (
        role_with_inline_policy["id"] is not assume_and_permission_boundary_role["id"]
    )
    assert role_with_inline_policy["id"] is not role_with_attached_policy["id"]

    # plain role
    plain_role_config = (
        role_config_query.backends[DEFAULT_ACCOUNT_ID]["global"]
        .roles[plain_role["id"]]
        .to_config_dict()
    )
    assert plain_role_config["version"] == "1.3"
    assert plain_role_config["configurationItemStatus"] == "ResourceDiscovered"
    assert plain_role_config["configurationStateId"] is not None
    assert plain_role_config["arn"] == "arn:aws:iam::123456789012:role/plain_role"
    assert plain_role_config["resourceType"] == "AWS::IAM::Role"
    assert plain_role_config["resourceId"] == "plain_role"
    assert plain_role_config["resourceName"] == "plain_role"
    assert plain_role_config["awsRegion"] == "global"
    assert plain_role_config["availabilityZone"] == "Not Applicable"
    assert plain_role_config["resourceCreationTime"] is not None
    assert plain_role_config["tags"] == {"foo": {"Key": "foo", "Value": "bar"}}
    assert plain_role_config["configuration"]["path"] == "/"
    assert plain_role_config["configuration"]["roleName"] == "plain_role"
    assert plain_role_config["configuration"]["roleId"] == plain_role["id"]
    assert plain_role_config["configuration"]["arn"] == plain_role_config["arn"]
    assert plain_role_config["configuration"]["assumeRolePolicyDocument"] is None
    assert plain_role_config["configuration"]["instanceProfileList"] == []
    assert plain_role_config["configuration"]["rolePolicyList"] == []
    assert plain_role_config["configuration"]["attachedManagedPolicies"] == []
    assert plain_role_config["configuration"]["permissionsBoundary"] is None
    assert plain_role_config["configuration"]["tags"] == [
        {"key": "foo", "value": "bar"}
    ]
    assert plain_role_config["supplementaryConfiguration"] == {}

    # assume_role
    assume_role_config = (
        role_config_query.backends[DEFAULT_ACCOUNT_ID]["global"]
        .roles[assume_role["id"]]
        .to_config_dict()
    )
    assert assume_role_config["arn"] == "arn:aws:iam::123456789012:role/assume_role"
    assert assume_role_config["resourceId"] == "assume_role"
    assert assume_role_config["resourceName"] == "assume_role"
    assert assume_role_config["configuration"][
        "assumeRolePolicyDocument"
    ] == parse.quote(json.dumps(basic_assume_role))

    # assume_and_permission_boundary_role
    assume_and_permission_boundary_role_config = (
        role_config_query.backends[DEFAULT_ACCOUNT_ID]["global"]
        .roles[assume_and_permission_boundary_role["id"]]
        .to_config_dict()
    )
    assert (
        assume_and_permission_boundary_role_config["arn"]
        == "arn:aws:iam::123456789012:role/assume_and_permission_boundary_role"
    )
    assert (
        assume_and_permission_boundary_role_config["resourceId"]
        == "assume_and_permission_boundary_role"
    )
    assert (
        assume_and_permission_boundary_role_config["resourceName"]
        == "assume_and_permission_boundary_role"
    )
    assert assume_and_permission_boundary_role_config["configuration"][
        "assumeRolePolicyDocument"
    ] == parse.quote(json.dumps(basic_assume_role))
    assert (
        assume_and_permission_boundary_role_config["configuration"][
            "permissionsBoundary"
        ]
        == policy_arn
    )

    # role_with_attached_policy
    role_with_attached_policy_config = (
        role_config_query.backends[DEFAULT_ACCOUNT_ID]["global"]
        .roles[role_with_attached_policy["id"]]
        .to_config_dict()
    )
    assert (
        role_with_attached_policy_config["arn"]
        == "arn:aws:iam::123456789012:role/role_with_attached_policy"
    )
    assert role_with_attached_policy_config["configuration"][
        "attachedManagedPolicies"
    ] == [{"policyArn": policy_arn, "policyName": "basic_policy"}]

    # role_with_inline_policy
    role_with_inline_policy_config = (
        role_config_query.backends[DEFAULT_ACCOUNT_ID]["global"]
        .roles[role_with_inline_policy["id"]]
        .to_config_dict()
    )
    assert (
        role_with_inline_policy_config["arn"]
        == "arn:aws:iam::123456789012:role/role_with_inline_policy"
    )
    assert role_with_inline_policy_config["configuration"]["rolePolicyList"] == [
        {
            "policyName": "inline_policy",
            "policyDocument": parse.quote(json.dumps(basic_policy)),
        }
    ]


@mock_iam
@mock_config
def test_role_config_client():
    from moto.iam.utils import random_role_id

    CONFIG_REGIONS = boto3.Session().get_available_regions("config")

    iam_client = boto3.client("iam", region_name="us-west-2")
    config_client = boto3.client("config", region_name="us-west-2")

    all_account_aggregation_source = {
        "AccountIds": [ACCOUNT_ID],
        "AllAwsRegions": True,
    }

    two_region_account_aggregation_source = {
        "AccountIds": [ACCOUNT_ID],
        "AwsRegions": ["us-east-1", "us-west-2"],
    }

    config_client.put_configuration_aggregator(
        ConfigurationAggregatorName="test_aggregator",
        AccountAggregationSources=[all_account_aggregation_source],
    )

    config_client.put_configuration_aggregator(
        ConfigurationAggregatorName="test_aggregator_two_regions",
        AccountAggregationSources=[two_region_account_aggregation_source],
    )

    result = config_client.list_discovered_resources(resourceType="AWS::IAM::Role")
    assert not result["resourceIdentifiers"]

    # Make 10 policies
    roles = []
    num_roles = 10
    for ix in range(1, num_roles + 1):
        this_policy = iam_client.create_role(
            RoleName=f"role{ix}",
            Path="/",
            Description=f"role{ix}",
            AssumeRolePolicyDocument=json.dumps("{ }"),
        )
        roles.append(
            {
                "id": this_policy["Role"]["RoleId"],
                "name": this_policy["Role"]["RoleName"],
            }
        )

    assert len(roles) == num_roles

    # Test non-aggregated query: (everything is getting a random id, so we can't test names by ordering)
    result = config_client.list_discovered_resources(
        resourceType="AWS::IAM::Role", limit=1
    )
    first_result = result["resourceIdentifiers"][0]["resourceId"]
    assert result["resourceIdentifiers"][0]["resourceType"] == "AWS::IAM::Role"
    assert len(first_result) == len(random_role_id(DEFAULT_ACCOUNT_ID))

    # Test non-aggregated pagination
    assert (
        config_client.list_discovered_resources(
            resourceType="AWS::IAM::Role", limit=1, nextToken=result["nextToken"]
        )["resourceIdentifiers"][0]["resourceId"]
    ) != first_result

    # Test aggregated query - by `Limit=len(CONFIG_REGIONS)`, we should get a single policy duplicated across all regions
    agg_result = config_client.list_aggregate_discovered_resources(
        ResourceType="AWS::IAM::Role",
        ConfigurationAggregatorName="test_aggregator",
        Limit=len(CONFIG_REGIONS),
    )
    assert len(agg_result["ResourceIdentifiers"]) == len(CONFIG_REGIONS)

    agg_name = None
    agg_id = None
    for resource in agg_result["ResourceIdentifiers"]:
        assert resource["ResourceType"] == "AWS::IAM::Role"
        assert resource["SourceRegion"] in CONFIG_REGIONS
        assert resource["SourceAccountId"] == ACCOUNT_ID
        if agg_id:
            assert resource["ResourceId"] == agg_id
        if agg_name:
            assert resource["ResourceName"] == agg_name
        agg_name = resource["ResourceName"]
        agg_id = resource["ResourceId"]

    # Test aggregated pagination
    for resource in config_client.list_aggregate_discovered_resources(
        ConfigurationAggregatorName="test_aggregator",
        ResourceType="AWS::IAM::Role",
        NextToken=agg_result["NextToken"],
    )["ResourceIdentifiers"]:
        assert resource["ResourceId"] != agg_id

    # Test non-aggregated resource name/id filter
    assert (
        config_client.list_discovered_resources(
            resourceType="AWS::IAM::Role", resourceName=roles[1]["name"], limit=1
        )["resourceIdentifiers"][0]["resourceName"]
        == roles[1]["name"]
    )

    assert (
        config_client.list_discovered_resources(
            resourceType="AWS::IAM::Role", resourceIds=[roles[0]["id"]], limit=1
        )["resourceIdentifiers"][0]["resourceName"]
        == roles[0]["name"]
    )

    # Test aggregated resource name/id filter
    agg_name_filter = config_client.list_aggregate_discovered_resources(
        ConfigurationAggregatorName="test_aggregator",
        ResourceType="AWS::IAM::Role",
        Filters={"ResourceName": roles[5]["name"]},
    )
    assert len(agg_name_filter["ResourceIdentifiers"]) == len(CONFIG_REGIONS)
    assert agg_name_filter["ResourceIdentifiers"][0]["ResourceId"] == roles[5]["id"]

    agg_name_filter = config_client.list_aggregate_discovered_resources(
        ConfigurationAggregatorName="test_aggregator_two_regions",
        ResourceType="AWS::IAM::Role",
        Filters={"ResourceName": roles[5]["name"]},
    )
    assert len(agg_name_filter["ResourceIdentifiers"]) == len(
        two_region_account_aggregation_source["AwsRegions"]
    )
    assert agg_name_filter["ResourceIdentifiers"][0]["ResourceId"] == roles[5]["id"]

    agg_id_filter = config_client.list_aggregate_discovered_resources(
        ConfigurationAggregatorName="test_aggregator",
        ResourceType="AWS::IAM::Role",
        Filters={"ResourceId": roles[4]["id"]},
    )

    assert len(agg_id_filter["ResourceIdentifiers"]) == len(CONFIG_REGIONS)
    assert agg_id_filter["ResourceIdentifiers"][0]["ResourceName"] == roles[4]["name"]

    agg_name_filter = config_client.list_aggregate_discovered_resources(
        ConfigurationAggregatorName="test_aggregator_two_regions",
        ResourceType="AWS::IAM::Role",
        Filters={"ResourceId": roles[5]["id"]},
    )
    assert len(agg_name_filter["ResourceIdentifiers"]) == len(
        two_region_account_aggregation_source["AwsRegions"]
    )
    assert agg_name_filter["ResourceIdentifiers"][0]["ResourceName"] == roles[5]["name"]

    # Test non-aggregated resource name/id filter
    assert (
        config_client.list_discovered_resources(
            resourceType="AWS::IAM::Role", resourceName=roles[1]["name"], limit=1
        )["resourceIdentifiers"][0]["resourceName"]
        == roles[1]["name"]
    )
    assert (
        config_client.list_discovered_resources(
            resourceType="AWS::IAM::Role", resourceIds=[roles[0]["id"]], limit=1
        )["resourceIdentifiers"][0]["resourceName"]
        == roles[0]["name"]
    )

    # Test aggregated resource name/id filter
    assert (
        config_client.list_aggregate_discovered_resources(
            ConfigurationAggregatorName="test_aggregator",
            ResourceType="AWS::IAM::Role",
            Filters={"ResourceName": roles[5]["name"]},
            Limit=1,
        )["ResourceIdentifiers"][0]["ResourceName"]
        == roles[5]["name"]
    )

    assert (
        config_client.list_aggregate_discovered_resources(
            ConfigurationAggregatorName="test_aggregator",
            ResourceType="AWS::IAM::Role",
            Filters={"ResourceId": roles[4]["id"]},
            Limit=1,
        )["ResourceIdentifiers"][0]["ResourceName"]
        == roles[4]["name"]
    )

    # Test name/id filter with pagination
    first_call = config_client.list_discovered_resources(
        resourceType="AWS::IAM::Role",
        resourceIds=[roles[1]["id"], roles[2]["id"]],
        limit=1,
    )

    assert first_call["nextToken"] in [roles[1]["id"], roles[2]["id"]]
    assert first_call["resourceIdentifiers"][0]["resourceName"] in [
        roles[1]["name"],
        roles[2]["name"],
    ]
    second_call = config_client.list_discovered_resources(
        resourceType="AWS::IAM::Role",
        resourceIds=[roles[1]["id"], roles[2]["id"]],
        limit=1,
        nextToken=first_call["nextToken"],
    )
    assert "nextToken" not in second_call
    assert first_call["resourceIdentifiers"][0]["resourceName"] in [
        roles[1]["name"],
        roles[2]["name"],
    ]
    assert (
        first_call["resourceIdentifiers"][0]["resourceName"]
        != second_call["resourceIdentifiers"][0]["resourceName"]
    )

    # Test non-aggregated batch get
    assert (
        config_client.batch_get_resource_config(
            resourceKeys=[
                {"resourceType": "AWS::IAM::Role", "resourceId": roles[0]["id"]}
            ]
        )["baseConfigurationItems"][0]["resourceName"]
        == roles[0]["name"]
    )

    # Test aggregated batch get
    assert (
        config_client.batch_get_aggregate_resource_config(
            ConfigurationAggregatorName="test_aggregator",
            ResourceIdentifiers=[
                {
                    "SourceAccountId": ACCOUNT_ID,
                    "SourceRegion": "us-east-1",
                    "ResourceId": roles[1]["id"],
                    "ResourceType": "AWS::IAM::Role",
                }
            ],
        )["BaseConfigurationItems"][0]["resourceName"]
        == roles[1]["name"]
    )


@mock_iam
def test_policy_list_config_discovered_resources():
    from moto.iam.config import policy_config_query

    # Without any policies
    assert policy_config_query.list_config_service_resources(
        DEFAULT_ACCOUNT_ID, None, None, 100, None
    ) == (
        [],
        None,
    )

    basic_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {"Action": ["ec2:DeleteKeyPair"], "Effect": "Deny", "Resource": "*"}
        ],
    }

    # Make 3 policies
    policies = []
    num_policies = 3
    for ix in range(1, num_policies + 1):
        this_policy = policy_config_query.backends[DEFAULT_ACCOUNT_ID][
            "global"
        ].create_policy(
            description=f"policy{ix}",
            path="",
            policy_document=json.dumps(basic_policy),
            policy_name=f"policy{ix}",
            tags=[],
        )
        policies.append({"id": this_policy.id, "name": this_policy.name})

    assert len(policies) == num_policies

    # We expect the backend to have arns as their keys
    for backend_key in list(
        policy_config_query.backends[DEFAULT_ACCOUNT_ID][
            "global"
        ].managed_policies.keys()
    ):
        assert backend_key.startswith("arn:aws:iam::")

    result = policy_config_query.list_config_service_resources(
        DEFAULT_ACCOUNT_ID, None, None, 100, None
    )[0]
    assert len(result) == num_policies

    policy = result[0]
    assert policy["type"] == "AWS::IAM::Policy"
    assert policy["id"] in list(map(lambda p: p["id"], policies))
    assert policy["name"] in list(map(lambda p: p["name"], policies))
    assert policy["region"] == "global"

    # test passing list of resource ids
    resource_ids = policy_config_query.list_config_service_resources(
        DEFAULT_ACCOUNT_ID, [policies[0]["id"], policies[1]["id"]], None, 100, None
    )[0]
    assert len(resource_ids) == 2

    # test passing a single resource name
    resource_name = policy_config_query.list_config_service_resources(
        DEFAULT_ACCOUNT_ID, None, policies[0]["name"], 100, None
    )[0]
    assert len(resource_name) == 1
    assert resource_name[0]["id"] == policies[0]["id"]
    assert resource_name[0]["name"] == policies[0]["name"]

    # test passing a single resource name AND some resource id's
    both_filter_good = policy_config_query.list_config_service_resources(
        DEFAULT_ACCOUNT_ID,
        [policies[0]["id"], policies[1]["id"]],
        policies[0]["name"],
        100,
        None,
    )[0]
    assert len(both_filter_good) == 1
    assert both_filter_good[0]["id"] == policies[0]["id"]
    assert both_filter_good[0]["name"] == policies[0]["name"]

    both_filter_bad = policy_config_query.list_config_service_resources(
        DEFAULT_ACCOUNT_ID,
        [policies[0]["id"], policies[1]["id"]],
        policies[2]["name"],
        100,
        None,
    )[0]
    assert len(both_filter_bad) == 0


@mock_iam
def test_policy_config_dict():
    from moto.iam.config import role_config_query, policy_config_query
    from moto.iam.utils import random_policy_id

    # Without any roles
    assert not policy_config_query.get_config_resource(
        DEFAULT_ACCOUNT_ID, "arn:aws:iam::123456789012:policy/basic_policy"
    )
    assert policy_config_query.list_config_service_resources(
        DEFAULT_ACCOUNT_ID, None, None, 100, None
    ) == (
        [],
        None,
    )

    basic_policy = {
        "Version": "2012-10-17",
        "Statement": [{"Action": ["ec2:*"], "Effect": "Allow", "Resource": "*"}],
    }

    basic_policy_v2 = {
        "Version": "2012-10-17",
        "Statement": [
            {"Action": ["ec2:*", "s3:*"], "Effect": "Allow", "Resource": "*"}
        ],
    }

    policy_arn = (
        policy_config_query.backends[DEFAULT_ACCOUNT_ID]["global"]
        .create_policy(
            description="basic_policy",
            path="/",
            policy_document=json.dumps(basic_policy),
            policy_name="basic_policy",
            tags=[],
        )
        .arn
    )

    policy_id = policy_config_query.list_config_service_resources(
        DEFAULT_ACCOUNT_ID, None, None, 100, None
    )[0][0]["id"]
    assert len(policy_id) == len(random_policy_id())

    assert policy_arn == "arn:aws:iam::123456789012:policy/basic_policy"
    assert (
        policy_config_query.get_config_resource(DEFAULT_ACCOUNT_ID, policy_id)
        is not None
    )

    # Create a new version
    policy_config_query.backends[DEFAULT_ACCOUNT_ID]["global"].create_policy_version(
        policy_arn, json.dumps(basic_policy_v2), "true"
    )

    # Create role to trigger attachment
    role_config_query.backends[DEFAULT_ACCOUNT_ID]["global"].create_role(
        role_name="role_with_attached_policy",
        assume_role_policy_document=None,
        path="/",
        permissions_boundary=None,
        description="role_with_attached_policy",
        tags=[],
        max_session_duration=3600,
    )
    role_config_query.backends[DEFAULT_ACCOUNT_ID]["global"].attach_role_policy(
        policy_arn, "role_with_attached_policy"
    )

    policy = (
        role_config_query.backends[DEFAULT_ACCOUNT_ID]["global"]
        .managed_policies["arn:aws:iam::123456789012:policy/basic_policy"]
        .to_config_dict()
    )
    assert policy["version"] == "1.3"
    assert policy["configurationItemCaptureTime"] is not None
    assert policy["configurationItemStatus"] == "OK"
    assert policy["configurationStateId"] is not None
    assert policy["arn"] == "arn:aws:iam::123456789012:policy/basic_policy"
    assert policy["resourceType"] == "AWS::IAM::Policy"
    assert len(policy["resourceId"]) == len(random_policy_id())
    assert policy["resourceName"] == "basic_policy"
    assert policy["awsRegion"] == "global"
    assert policy["availabilityZone"] == "Not Applicable"
    assert policy["resourceCreationTime"] is not None
    assert policy["configuration"]["policyName"] == policy["resourceName"]
    assert policy["configuration"]["policyId"] == policy["resourceId"]
    assert policy["configuration"]["arn"] == policy["arn"]
    assert policy["configuration"]["path"] == "/"
    assert policy["configuration"]["defaultVersionId"] == "v2"
    assert policy["configuration"]["attachmentCount"] == 1
    assert policy["configuration"]["permissionsBoundaryUsageCount"] == 0
    assert policy["configuration"]["isAttachable"] is True
    assert policy["configuration"]["description"] == "basic_policy"
    assert policy["configuration"]["createDate"] is not None
    assert policy["configuration"]["updateDate"] is not None
    assert policy["configuration"]["policyVersionList"] == [
        {
            "document": str(parse.quote(json.dumps(basic_policy))),
            "versionId": "v1",
            "isDefaultVersion": False,
            "createDate": policy["configuration"]["policyVersionList"][0]["createDate"],
        },
        {
            "document": str(parse.quote(json.dumps(basic_policy_v2))),
            "versionId": "v2",
            "isDefaultVersion": True,
            "createDate": policy["configuration"]["policyVersionList"][1]["createDate"],
        },
    ]
    assert policy["supplementaryConfiguration"] == {}


@mock_iam
@mock_config
def test_policy_config_client():
    from moto.iam.utils import random_policy_id

    CONFIG_REGIONS = boto3.Session().get_available_regions("config")

    basic_policy = {
        "Version": "2012-10-17",
        "Statement": [{"Action": ["ec2:*"], "Effect": "Allow", "Resource": "*"}],
    }

    iam_client = boto3.client("iam", region_name="us-west-2")
    config_client = boto3.client("config", region_name="us-west-2")

    all_account_aggregation_source = {
        "AccountIds": [ACCOUNT_ID],
        "AllAwsRegions": True,
    }

    two_region_account_aggregation_source = {
        "AccountIds": [ACCOUNT_ID],
        "AwsRegions": ["us-east-1", "us-west-2"],
    }

    config_client.put_configuration_aggregator(
        ConfigurationAggregatorName="test_aggregator",
        AccountAggregationSources=[all_account_aggregation_source],
    )

    config_client.put_configuration_aggregator(
        ConfigurationAggregatorName="test_aggregator_two_regions",
        AccountAggregationSources=[two_region_account_aggregation_source],
    )

    result = config_client.list_discovered_resources(resourceType="AWS::IAM::Policy")
    assert not result["resourceIdentifiers"]

    # Make 10 policies
    policies = []
    num_policies = 10
    for ix in range(1, num_policies + 1):
        this_policy = iam_client.create_policy(
            PolicyName=f"policy{ix}",
            Path="/",
            PolicyDocument=json.dumps(basic_policy),
            Description=f"policy{ix}",
        )
        policies.append(
            {
                "id": this_policy["Policy"]["PolicyId"],
                "name": this_policy["Policy"]["PolicyName"],
            }
        )

    assert len(policies) == num_policies

    # Test non-aggregated query: (everything is getting a random id, so we can't test names by ordering)
    result = config_client.list_discovered_resources(
        resourceType="AWS::IAM::Policy", limit=1
    )
    first_result = result["resourceIdentifiers"][0]["resourceId"]
    assert result["resourceIdentifiers"][0]["resourceType"] == "AWS::IAM::Policy"
    assert len(first_result) == len(random_policy_id())

    # Test non-aggregated pagination
    assert (
        config_client.list_discovered_resources(
            resourceType="AWS::IAM::Policy", limit=1, nextToken=result["nextToken"]
        )["resourceIdentifiers"][0]["resourceId"]
    ) != first_result

    # Test aggregated query - by `Limit=len(CONFIG_REGIONS)`, we should get a single policy duplicated across all regions
    agg_result = config_client.list_aggregate_discovered_resources(
        ResourceType="AWS::IAM::Policy",
        ConfigurationAggregatorName="test_aggregator",
        Limit=len(CONFIG_REGIONS),
    )
    assert len(agg_result["ResourceIdentifiers"]) == len(CONFIG_REGIONS)

    agg_name = None
    agg_id = None
    for resource in agg_result["ResourceIdentifiers"]:
        assert resource["ResourceType"] == "AWS::IAM::Policy"
        assert resource["SourceRegion"] in CONFIG_REGIONS
        assert resource["SourceAccountId"] == ACCOUNT_ID
        if agg_id:
            assert resource["ResourceId"] == agg_id
        if agg_name:
            assert resource["ResourceName"] == agg_name
        agg_name = resource["ResourceName"]
        agg_id = resource["ResourceId"]

    # Test aggregated pagination
    for resource in config_client.list_aggregate_discovered_resources(
        ConfigurationAggregatorName="test_aggregator",
        ResourceType="AWS::IAM::Policy",
        Limit=1,
        NextToken=agg_result["NextToken"],
    )["ResourceIdentifiers"]:
        assert resource["ResourceId"] != agg_id

    # Test non-aggregated resource name/id filter
    assert (
        config_client.list_discovered_resources(
            resourceType="AWS::IAM::Policy", resourceName=policies[1]["name"], limit=1
        )["resourceIdentifiers"][0]["resourceName"]
        == policies[1]["name"]
    )

    assert (
        config_client.list_discovered_resources(
            resourceType="AWS::IAM::Policy", resourceIds=[policies[0]["id"]], limit=1
        )["resourceIdentifiers"][0]["resourceName"]
        == policies[0]["name"]
    )

    # Test aggregated resource name/id filter
    agg_name_filter = config_client.list_aggregate_discovered_resources(
        ConfigurationAggregatorName="test_aggregator",
        ResourceType="AWS::IAM::Policy",
        Filters={"ResourceName": policies[5]["name"]},
    )
    assert len(agg_name_filter["ResourceIdentifiers"]) == len(CONFIG_REGIONS)
    assert (
        agg_name_filter["ResourceIdentifiers"][0]["ResourceName"] == policies[5]["name"]
    )

    agg_name_filter = config_client.list_aggregate_discovered_resources(
        ConfigurationAggregatorName="test_aggregator_two_regions",
        ResourceType="AWS::IAM::Policy",
        Filters={"ResourceName": policies[5]["name"]},
    )
    assert len(agg_name_filter["ResourceIdentifiers"]) == len(
        two_region_account_aggregation_source["AwsRegions"]
    )
    assert agg_name_filter["ResourceIdentifiers"][0]["ResourceId"] == policies[5]["id"]

    agg_id_filter = config_client.list_aggregate_discovered_resources(
        ConfigurationAggregatorName="test_aggregator",
        ResourceType="AWS::IAM::Policy",
        Filters={"ResourceId": policies[4]["id"]},
    )

    assert len(agg_id_filter["ResourceIdentifiers"]) == len(CONFIG_REGIONS)
    assert (
        agg_id_filter["ResourceIdentifiers"][0]["ResourceName"] == policies[4]["name"]
    )

    agg_name_filter = config_client.list_aggregate_discovered_resources(
        ConfigurationAggregatorName="test_aggregator_two_regions",
        ResourceType="AWS::IAM::Policy",
        Filters={"ResourceId": policies[5]["id"]},
    )
    assert len(agg_name_filter["ResourceIdentifiers"]) == len(
        two_region_account_aggregation_source["AwsRegions"]
    )
    assert (
        agg_name_filter["ResourceIdentifiers"][0]["ResourceName"] == policies[5]["name"]
    )

    # Test name/id filter with pagination
    first_call = config_client.list_discovered_resources(
        resourceType="AWS::IAM::Policy",
        resourceIds=[policies[1]["id"], policies[2]["id"]],
        limit=1,
    )

    assert first_call["nextToken"] in [policies[1]["id"], policies[2]["id"]]
    assert first_call["resourceIdentifiers"][0]["resourceName"] in [
        policies[1]["name"],
        policies[2]["name"],
    ]
    second_call = config_client.list_discovered_resources(
        resourceType="AWS::IAM::Policy",
        resourceIds=[policies[1]["id"], policies[2]["id"]],
        limit=1,
        nextToken=first_call["nextToken"],
    )
    assert "nextToken" not in second_call
    assert first_call["resourceIdentifiers"][0]["resourceName"] in [
        policies[1]["name"],
        policies[2]["name"],
    ]
    assert (
        first_call["resourceIdentifiers"][0]["resourceName"]
        != second_call["resourceIdentifiers"][0]["resourceName"]
    )

    # Test non-aggregated batch get
    assert (
        config_client.batch_get_resource_config(
            resourceKeys=[
                {"resourceType": "AWS::IAM::Policy", "resourceId": policies[7]["id"]}
            ]
        )["baseConfigurationItems"][0]["resourceName"]
        == policies[7]["name"]
    )

    # Test aggregated batch get
    assert (
        config_client.batch_get_aggregate_resource_config(
            ConfigurationAggregatorName="test_aggregator",
            ResourceIdentifiers=[
                {
                    "SourceAccountId": ACCOUNT_ID,
                    "SourceRegion": "us-east-2",
                    "ResourceId": policies[8]["id"],
                    "ResourceType": "AWS::IAM::Policy",
                }
            ],
        )["BaseConfigurationItems"][0]["resourceName"]
        == policies[8]["name"]
    )


@mock_iam()
def test_list_roles_with_more_than_100_roles_no_max_items_defaults_to_100():
    iam = boto3.client("iam", region_name="us-east-1")
    for i in range(150):
        iam.create_role(
            RoleName=f"test_role_{i}", AssumeRolePolicyDocument="some policy"
        )
    response = iam.list_roles()
    roles = response["Roles"]

    assert response["IsTruncated"] is True
    assert len(roles) == 100


@mock_iam()
def test_list_roles_max_item_and_marker_values_adhered():
    iam = boto3.client("iam", region_name="us-east-1")
    for i in range(10):
        iam.create_role(
            RoleName=f"test_role_{i}", AssumeRolePolicyDocument="some policy"
        )
    response = iam.list_roles(MaxItems=2)
    roles = response["Roles"]

    assert response["IsTruncated"] is True
    assert len(roles) == 2

    response = iam.list_roles(Marker=response["Marker"])
    roles = response["Roles"]

    assert response["IsTruncated"] is False
    assert len(roles) == 8


@mock_iam()
def test_list_roles_path_prefix_value_adhered():
    iam = boto3.client("iam", region_name="us-east-1")
    iam.create_role(
        RoleName="test_role_without_path", AssumeRolePolicyDocument="some policy"
    )
    iam.create_role(
        RoleName="test_role_with_path",
        AssumeRolePolicyDocument="some policy",
        Path="/TestPath/",
    )

    response = iam.list_roles(PathPrefix="/TestPath/")
    roles = response["Roles"]

    assert len(roles) == 1
    assert roles[0]["RoleName"] == "test_role_with_path"


@mock_iam()
def test_list_roles_none_found_returns_empty_list():
    iam = boto3.client("iam", region_name="us-east-1")

    response = iam.list_roles()
    roles = response["Roles"]
    assert len(roles) == 0

    response = iam.list_roles(PathPrefix="/TestPath")
    roles = response["Roles"]
    assert len(roles) == 0

    response = iam.list_roles(Marker="10")
    roles = response["Roles"]
    assert len(roles) == 0

    response = iam.list_roles(MaxItems=10)
    roles = response["Roles"]
    assert len(roles) == 0


@mock_iam()
def test_list_roles():
    conn = boto3.client("iam", region_name="us-east-1")
    for desc in ["", "desc"]:
        resp = conn.create_role(
            RoleName=f"role_{desc}",
            AssumeRolePolicyDocument="some policy",
            Description=desc,
        )
        assert resp["Role"]["Description"] == desc
    conn.create_role(RoleName="role3", AssumeRolePolicyDocument="sp")

    # Ensure the Description is included in role listing as well
    all_roles = conn.list_roles()["Roles"]

    role1 = next(r for r in all_roles if r["RoleName"] == "role_")
    role2 = next(r for r in all_roles if r["RoleName"] == "role_desc")
    role3 = next(r for r in all_roles if r["RoleName"] == "role3")
    assert role1["Description"] == ""
    assert role2["Description"] == "desc"
    assert "Description" not in role3

    assert all([role["CreateDate"] for role in all_roles])
    assert all([role["MaxSessionDuration"] for role in all_roles])


@mock_iam()
def test_create_user_with_tags():
    conn = boto3.client("iam", region_name="us-east-1")
    user_name = "test-user"
    tags = [
        {"Key": "somekey", "Value": "somevalue"},
        {"Key": "someotherkey", "Value": "someothervalue"},
    ]
    resp = conn.create_user(UserName=user_name, Tags=tags)
    assert resp["User"]["Tags"] == tags
    resp = conn.list_user_tags(UserName=user_name)
    assert resp["Tags"] == tags
    resp = conn.get_user(UserName=user_name)
    assert resp["User"]["Tags"] == tags
    resp = conn.create_user(UserName="test-create-user-no-tags")
    assert "Tags" not in resp["User"]


@mock_iam
def test_tag_user():
    # given
    client = boto3.client("iam", region_name="eu-central-1")
    name = "test-user"
    tags = sorted(
        [{"Key": "key", "Value": "value"}, {"Key": "key-2", "Value": "value-2"}],
        key=lambda item: item["Key"],
    )
    client.create_user(UserName=name)

    # when
    client.tag_user(UserName=name, Tags=tags)

    # then
    response = client.list_user_tags(UserName=name)
    assert sorted(response["Tags"], key=lambda item: item["Key"]) == tags


@mock_iam
def test_tag_user_error_unknown_user_name():
    # given
    client = boto3.client("iam", region_name="eu-central-1")
    name = "unknown"

    # when
    with pytest.raises(ClientError) as e:
        client.tag_user(UserName=name, Tags=[{"Key": "key", "Value": "value"}])

    # then
    ex = e.value
    assert ex.operation_name == "TagUser"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 404
    assert "NoSuchEntity" in ex.response["Error"]["Code"]
    assert (
        ex.response["Error"]["Message"] == f"The user with name {name} cannot be found."
    )


@mock_iam
def test_untag_user():
    # given
    client = boto3.client("iam", region_name="eu-central-1")
    name = "test-user"
    client.create_user(
        UserName=name,
        Tags=[{"Key": "key", "Value": "value"}, {"Key": "key-2", "Value": "value"}],
    )

    # when
    client.untag_user(UserName=name, TagKeys=["key-2"])

    # then
    response = client.list_user_tags(UserName=name)
    assert response["Tags"] == [{"Key": "key", "Value": "value"}]


@mock_iam
def test_untag_user_error_unknown_user_name():
    # given
    client = boto3.client("iam", region_name="eu-central-1")
    name = "unknown"

    # when
    with pytest.raises(ClientError) as e:
        client.untag_user(UserName=name, TagKeys=["key"])

    # then
    ex = e.value
    assert ex.operation_name == "UntagUser"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 404
    assert "NoSuchEntity" in ex.response["Error"]["Code"]
    assert (
        ex.response["Error"]["Message"] == f"The user with name {name} cannot be found."
    )


@mock_iam
@pytest.mark.parametrize(
    "service,cased",
    [
        ("autoscaling", "AutoScaling"),
        ("elasticbeanstalk", "ElasticBeanstalk"),
        (
            "custom-resource.application-autoscaling",
            "ApplicationAutoScaling_CustomResource",
        ),
        ("other", "other"),
    ],
)
def test_create_service_linked_role(service, cased):
    client = boto3.client("iam", region_name="eu-central-1")

    resp = client.create_service_linked_role(
        AWSServiceName=f"{service}.amazonaws.com", Description="desc"
    )["Role"]

    assert resp["RoleName"] == f"AWSServiceRoleFor{cased}"


@mock_iam
def test_create_service_linked_role__with_suffix():
    client = boto3.client("iam", region_name="eu-central-1")

    resp = client.create_service_linked_role(
        AWSServiceName="autoscaling.amazonaws.com",
        CustomSuffix="suf",
        Description="desc",
    )["Role"]

    assert resp["RoleName"].endswith("_suf")
    assert resp["Description"] == "desc"
    policy_doc = resp["AssumeRolePolicyDocument"]
    assert policy_doc["Statement"] == [
        {
            "Action": ["sts:AssumeRole"],
            "Effect": "Allow",
            "Principal": {"Service": ["autoscaling.amazonaws.com"]},
        }
    ]


@mock_iam
def test_delete_service_linked_role():
    client = boto3.client("iam", region_name="eu-central-1")

    role_name = client.create_service_linked_role(
        AWSServiceName="autoscaling.amazonaws.com",
        CustomSuffix="suf",
        Description="desc",
    )["Role"]["RoleName"]

    # Role exists
    client.get_role(RoleName=role_name)

    # Delete role
    resp = client.delete_service_linked_role(RoleName=role_name)

    # Role deletion should be successful
    resp = client.get_service_linked_role_deletion_status(
        DeletionTaskId=resp["DeletionTaskId"]
    )
    assert resp["Status"] == "SUCCEEDED"

    # Role no longer exists
    with pytest.raises(ClientError) as ex:
        client.get_role(RoleName=role_name)
    err = ex.value.response["Error"]
    assert err["Code"] == "NoSuchEntity"
    assert "not found" in err["Message"]
