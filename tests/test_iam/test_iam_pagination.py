from collections.abc import Callable
from typing import Any

import boto3
import pytest

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from tests.test_iam.test_iam_signing_certificates import create_certificate

POLICY_DOCUMENT = """{
    "Version": "2012-10-17",
    "Statement": [{"Effect": "Allow", "Action": "s3:ListBucket", "Resource": "*"}]
}"""
ASSUME_ROLE_POLICY = """{
    "Version": "2012-10-17",
    "Statement": [{"Effect": "Allow", "Principal": {"Service": "ec2.amazonaws.com"}, "Action": "sts:AssumeRole"}]
}"""
SSH_PUBLIC_KEY = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQ"
TAGS = [{"Key": f"key-{i}", "Value": f"value-{i}"} for i in range(3)]
POLICY_ARN = f"arn:aws:iam::{ACCOUNT_ID}:policy/policy"
OIDC_ARN = f"arn:aws:iam::{ACCOUNT_ID}:oidc-provider/example.com"


def _create_users(client: Any) -> None:
    for i in range(3):
        client.create_user(UserName=f"user-{i}")
        client.add_user_to_group(GroupName="group", UserName=f"user-{i}")


def _create_managed_policies(client: Any) -> None:
    for i in range(3):
        resp = client.create_policy(
            PolicyName=f"policy-{i}", PolicyDocument=POLICY_DOCUMENT
        )
        arn = resp["Policy"]["Arn"]
        client.attach_user_policy(UserName="user", PolicyArn=arn)
        client.attach_group_policy(GroupName="group", PolicyArn=arn)
        client.attach_role_policy(RoleName="role", PolicyArn=arn)


def _create_inline_policies(client: Any) -> None:
    for i in range(3):
        name = f"inline-{i}"
        doc = POLICY_DOCUMENT
        client.put_user_policy(UserName="user", PolicyName=name, PolicyDocument=doc)
        client.put_group_policy(GroupName="group", PolicyName=name, PolicyDocument=doc)
        client.put_role_policy(RoleName="role", PolicyName=name, PolicyDocument=doc)


def _create_groups(client: Any) -> None:
    for i in range(3):
        client.create_group(GroupName=f"group-{i}")
        client.add_user_to_group(GroupName=f"group-{i}", UserName="user")


def _create_instance_profiles(client: Any) -> None:
    for i in range(3):
        client.create_instance_profile(InstanceProfileName=f"profile-{i}")
        client.add_role_to_instance_profile(
            InstanceProfileName=f"profile-{i}", RoleName="role"
        )


def _create_access_keys(client: Any) -> None:
    # A user can have at most two access keys
    for _ in range(2):
        client.create_access_key(UserName="user")


def _create_mfa_devices(client: Any) -> None:
    for i in range(3):
        serial = client.create_virtual_mfa_device(VirtualMFADeviceName=f"mfa-{i}")[
            "VirtualMFADevice"
        ]["SerialNumber"]
        client.enable_mfa_device(
            UserName="user",
            SerialNumber=serial,
            AuthenticationCode1="123456",
            AuthenticationCode2="123456",
        )


def _create_policy_versions(client: Any) -> None:
    for _ in range(2):
        client.create_policy_version(
            PolicyArn=POLICY_ARN, PolicyDocument=POLICY_DOCUMENT
        )


def _create_roles(client: Any) -> None:
    for i in range(2):
        client.create_role(
            RoleName=f"role-{i}", AssumeRolePolicyDocument=ASSUME_ROLE_POLICY
        )


def _create_server_certificates(client: Any) -> None:
    for i in range(3):
        client.upload_server_certificate(
            ServerCertificateName=f"cert-{i}",
            CertificateBody="body",
            PrivateKey="key",
        )


def _create_signing_certificates(client: Any) -> None:
    for _ in range(2):
        client.upload_signing_certificate(
            UserName="user", CertificateBody=create_certificate()
        )


def _create_ssh_public_keys(client: Any) -> None:
    for i in range(3):
        client.upload_ssh_public_key(
            UserName="user", SSHPublicKeyBody=f"{SSH_PUBLIC_KEY}{i}"
        )


def _create_tags(client: Any) -> None:
    client.tag_user(UserName="user", Tags=TAGS)
    client.tag_role(RoleName="role", Tags=TAGS)
    client.tag_policy(PolicyArn=POLICY_ARN, Tags=TAGS)
    client.tag_open_id_connect_provider(OpenIDConnectProviderArn=OIDC_ARN, Tags=TAGS)


# (operation, kwargs, result_key, create_resources)
PAGINATED_OPERATIONS = [
    ("get_group", {"GroupName": "group"}, "Users", _create_users),
    ("list_access_keys", {"UserName": "user"}, "AccessKeyMetadata", _create_access_keys),
    ("list_account_aliases", {}, "AccountAliases", lambda c: None),
    ("list_attached_group_policies", {"GroupName": "group"}, "AttachedPolicies", _create_managed_policies),
    ("list_attached_role_policies", {"RoleName": "role"}, "AttachedPolicies", _create_managed_policies),
    ("list_attached_user_policies", {"UserName": "user"}, "AttachedPolicies", _create_managed_policies),
    ("list_group_policies", {"GroupName": "group"}, "PolicyNames", _create_inline_policies),
    ("list_groups", {}, "Groups", _create_groups),
    ("list_groups_for_user", {"UserName": "user"}, "Groups", _create_groups),
    ("list_instance_profiles", {}, "InstanceProfiles", _create_instance_profiles),
    ("list_instance_profiles_for_role", {"RoleName": "role"}, "InstanceProfiles", _create_instance_profiles),
    ("list_mfa_devices", {"UserName": "user"}, "MFADevices", _create_mfa_devices),
    ("list_open_id_connect_provider_tags", {"OpenIDConnectProviderArn": OIDC_ARN}, "Tags", _create_tags),
    ("list_policies", {"Scope": "Local"}, "Policies", _create_managed_policies),
    ("list_policy_tags", {"PolicyArn": POLICY_ARN}, "Tags", _create_tags),
    ("list_policy_versions", {"PolicyArn": POLICY_ARN}, "Versions", _create_policy_versions),
    ("list_role_policies", {"RoleName": "role"}, "PolicyNames", _create_inline_policies),
    ("list_role_tags", {"RoleName": "role"}, "Tags", _create_tags),
    ("list_roles", {}, "Roles", _create_roles),
    ("list_server_certificates", {}, "ServerCertificateMetadataList", _create_server_certificates),
    ("list_signing_certificates", {"UserName": "user"}, "Certificates", _create_signing_certificates),
    ("list_ssh_public_keys", {"UserName": "user"}, "SSHPublicKeys", _create_ssh_public_keys),
    ("list_user_policies", {"UserName": "user"}, "PolicyNames", _create_inline_policies),
    ("list_user_tags", {"UserName": "user"}, "Tags", _create_tags),
    ("list_users", {}, "Users", _create_users),
    ("list_virtual_mfa_devices", {}, "VirtualMFADevices", _create_mfa_devices),
]  # fmt: skip


@pytest.mark.parametrize(
    "operation,kwargs,result_key,create_resources",
    PAGINATED_OPERATIONS,
    ids=[operation for operation, *_ in PAGINATED_OPERATIONS],
)
@mock_aws
def test_pagination(
    operation: str,
    kwargs: dict[str, Any],
    result_key: str,
    create_resources: Callable[[Any], None],
) -> None:
    client = boto3.client("iam", region_name="us-east-1")
    # Baseline resources that the per-operation setup builds on
    client.create_user(UserName="user")
    client.create_group(GroupName="group")
    client.create_role(RoleName="role", AssumeRolePolicyDocument=ASSUME_ROLE_POLICY)
    client.create_policy(PolicyName="policy", PolicyDocument=POLICY_DOCUMENT)
    client.create_open_id_connect_provider(Url="https://example.com", ThumbprintList=[])
    client.create_account_alias(AccountAlias="alias")
    # Spin up the resources to be paged through
    create_resources(client)
    # Get the full result
    all_resources = getattr(client, operation)(**kwargs)[result_key]
    assert len(all_resources) >= 1
    # Get the full result via the paginator
    paginator = client.get_paginator(operation)
    pages = list(paginator.paginate(**kwargs, PaginationConfig={"PageSize": 1}))
    # We're using a page size of one, so we should have a page for each resource
    assert len(pages) == len(all_resources)
    # Per page assertions
    for page in pages[:-1]:
        assert page["IsTruncated"] is True
        assert page["Marker"]
    assert pages[-1]["IsTruncated"] is False
    assert "Marker" not in pages[-1]
    assert [item for page in pages for item in page[result_key]] == all_resources
