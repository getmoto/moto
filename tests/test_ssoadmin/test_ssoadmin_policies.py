import json

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.iam.aws_managed_policies import aws_managed_policies_data

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html

DUMMY_PERMISSIONSET_ID = (
    "arn:aws:sso:::permissionSet/ins-eeeeffffgggghhhh/ps-hhhhkkkkppppoooo"
)
DUMMY_INSTANCE_ARN = "arn:aws:sso:::instance/ins-aaaabbbbccccdddd"


@pytest.fixture(name="managed_policies")
def get_managed_policies():
    return json.loads(aws_managed_policies_data)


def create_permissionset(client) -> str:
    """Helper function to create a dummy permission set and returns the arn."""

    response = client.create_permission_set(
        Name="test-permission-set",
        InstanceArn=DUMMY_INSTANCE_ARN,
        Description="test permission set",
    )

    return response["PermissionSet"]["PermissionSetArn"]


@mock_aws
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


@mock_aws
def test_get_inline_policy_to_permission_set_no_policy():
    client = boto3.client("sso-admin", region_name="us-east-1")

    permission_set_arn = create_permissionset(client)

    response = client.get_inline_policy_for_permission_set(
        InstanceArn=DUMMY_INSTANCE_ARN,
        PermissionSetArn=permission_set_arn,
    )

    assert response["InlinePolicy"] == ""


@mock_aws
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


@mock_aws
def test_attach_managed_policy_to_permission_set():
    client = boto3.client("sso-admin", region_name="us-east-1")

    permission_set_arn = create_permissionset(client)
    permissionset_id = permission_set_arn.split("/")[-1]
    managed_policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"

    client.attach_managed_policy_to_permission_set(
        InstanceArn=DUMMY_INSTANCE_ARN,
        PermissionSetArn=permission_set_arn,
        ManagedPolicyArn=managed_policy_arn,
    )

    response = client.list_managed_policies_in_permission_set(
        InstanceArn=DUMMY_INSTANCE_ARN,
        PermissionSetArn=permission_set_arn,
    )

    assert response["AttachedManagedPolicies"][0]["Name"] == "AdministratorAccess"
    assert (
        response["AttachedManagedPolicies"][0]["Arn"]
        == "arn:aws:iam::aws:policy/AdministratorAccess"
    )

    # test for managed policy that is already attached
    with pytest.raises(ClientError) as e:
        client.attach_managed_policy_to_permission_set(
            InstanceArn=DUMMY_INSTANCE_ARN,
            PermissionSetArn=permission_set_arn,
            ManagedPolicyArn=managed_policy_arn,
        )
    err = e.value.response["Error"]
    assert err["Code"] == "ConflictException"
    assert (
        err["Message"]
        == f"Permission set with id {permissionset_id} already has a typed link attachment to a manged policy with {managed_policy_arn}"
    )

    # test for managed policy that does not exist
    not_exist_managed_policy_arn = "arn:aws:iam::aws:policy/DoesNotExist"
    with pytest.raises(ClientError) as e:
        client.attach_managed_policy_to_permission_set(
            InstanceArn=DUMMY_INSTANCE_ARN,
            PermissionSetArn=permission_set_arn,
            ManagedPolicyArn=not_exist_managed_policy_arn,
        )
    err = e.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert (
        err["Message"]
        == "Policy does not exist with ARN: arn:aws:iam::aws:policy/DoesNotExist"
    )


@mock_aws
def test_list_managed_policies_quota_limit(managed_policies):
    """
    Tests exceeding the managed policy quota limit.
    """
    managed_policies_to_attach = []
    policy_count = 0
    for policy_name in managed_policies:
        path = managed_policies[policy_name]["Path"]
        # only attach policies with path "/"
        if path != "/":
            continue
        managed_policies_to_attach.append(policy_name)
        policy_count += 1
        if policy_count >= 21:  # 20 is the quota limit
            break

    client = boto3.client("sso-admin", region_name="us-east-1")
    permission_set_arn = create_permissionset(client)
    permission_set_id = permission_set_arn.split("/")[-1]

    arn_string = "arn:aws:iam::aws:policy/"
    with pytest.raises(ClientError) as e:
        # the 21st policy should exceed the quota limit
        for managed_policy in managed_policies_to_attach:
            client.attach_managed_policy_to_permission_set(
                InstanceArn=DUMMY_INSTANCE_ARN,
                PermissionSetArn=permission_set_arn,
                ManagedPolicyArn=arn_string + managed_policy,
            )
    err = e.value.response["Error"]
    assert err["Code"] == "ServiceQuotaExceededException"
    assert (
        err["Message"]
        == f"You have exceeded AWS SSO limits. Cannot create ManagedPolicy more than 20 for id {permission_set_id}. Please refer to https://docs.aws.amazon.com/singlesignon/latest/userguide/limits.html"
    )


@mock_aws
def test_list_managed_policies_in_permission_set(managed_policies):
    """
    Tests functionality of listing aws managed policies attached to a permission set.
    This also tests the pagination functionality.
    """
    client = boto3.client("sso-admin", region_name="us-east-1")

    arn_string = "arn:aws:iam::aws:policy/"

    # create a dummy permission set
    permission_set_arn = create_permissionset(client)

    managed_policies_names = list(managed_policies.keys())

    # attach 3 good managed policies
    for idx in range(3):
        managed_policy_name = managed_policies_names[idx]

        client.attach_managed_policy_to_permission_set(
            InstanceArn=DUMMY_INSTANCE_ARN,
            PermissionSetArn=permission_set_arn,
            ManagedPolicyArn=arn_string + managed_policy_name,
        )

    response = client.list_managed_policies_in_permission_set(
        InstanceArn=DUMMY_INSTANCE_ARN,
        PermissionSetArn=permission_set_arn,
        MaxResults=2,
    )

    managed_policies = []

    assert len(response["AttachedManagedPolicies"]) == 2
    managed_policies.extend(response["AttachedManagedPolicies"])
    next_token = response["NextToken"]

    response = client.list_managed_policies_in_permission_set(
        InstanceArn=DUMMY_INSTANCE_ARN,
        PermissionSetArn=permission_set_arn,
        MaxResults=2,
        NextToken=next_token,
    )

    assert len(response["AttachedManagedPolicies"]) == 1
    managed_policies.extend(response["AttachedManagedPolicies"])

    # ensure the 3 unique managed policies were returned
    actual_managed_policy_names = [
        managed_policy["Name"] for managed_policy in managed_policies
    ]
    expected_managed_policy_names = managed_policies_names[:3]
    assert all(
        name in actual_managed_policy_names for name in expected_managed_policy_names
    )


@mock_aws
def test_detach_managed_policy_from_permission_set():
    client = boto3.client("sso-admin", region_name="us-east-1")
    permission_set_arn = create_permissionset(client)
    managed_policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"

    # test for managed policy that is not attached
    with pytest.raises(ClientError) as e:
        client.detach_managed_policy_from_permission_set(
            InstanceArn=DUMMY_INSTANCE_ARN,
            PermissionSetArn=permission_set_arn,
            ManagedPolicyArn=managed_policy_arn,
        )
    err = e.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert (
        err["Message"] == f"Could not find ManagedPolicy with arn {managed_policy_arn}"
    )

    # attach managed policy
    client.attach_managed_policy_to_permission_set(
        InstanceArn=DUMMY_INSTANCE_ARN,
        PermissionSetArn=permission_set_arn,
        ManagedPolicyArn=managed_policy_arn,
    )

    # detach managed policy
    client.detach_managed_policy_from_permission_set(
        InstanceArn=DUMMY_INSTANCE_ARN,
        PermissionSetArn=permission_set_arn,
        ManagedPolicyArn=managed_policy_arn,
    )

    # ensure managed policy is detached
    response = client.list_managed_policies_in_permission_set(
        InstanceArn=DUMMY_INSTANCE_ARN,
        PermissionSetArn=permission_set_arn,
    )

    assert len(response["AttachedManagedPolicies"]) == 0


@mock_aws
def test_attach_customer_managed_policy_reference_to_permission_set():
    client = boto3.client("sso-admin", region_name="us-east-1")
    permission_set_arn = create_permissionset(client)

    policy_name = "test-policy"
    policy_path = "/test-path/"

    client.attach_customer_managed_policy_reference_to_permission_set(
        InstanceArn=DUMMY_INSTANCE_ARN,
        PermissionSetArn=permission_set_arn,
        CustomerManagedPolicyReference={
            "Name": policy_name,
            "Path": policy_path,
        },
    )

    response = client.list_customer_managed_policy_references_in_permission_set(
        InstanceArn=DUMMY_INSTANCE_ARN,
        PermissionSetArn=permission_set_arn,
    )

    assert len(response["CustomerManagedPolicyReferences"]) == 1
    assert response["CustomerManagedPolicyReferences"][0]["Name"] == policy_name
    assert response["CustomerManagedPolicyReferences"][0]["Path"] == policy_path

    # test for customer managed policy that is already attached
    with pytest.raises(ClientError) as e:
        client.attach_customer_managed_policy_reference_to_permission_set(
            InstanceArn=DUMMY_INSTANCE_ARN,
            PermissionSetArn=permission_set_arn,
            CustomerManagedPolicyReference={
                "Name": policy_name,
                "Path": policy_path,
            },
        )
    err = e.value.response["Error"]
    assert err["Code"] == "ConflictException"
    assert (
        err["Message"]
        == f"Given customer managed policy with name: {policy_name}  and path {policy_path} already attached"
    )


@mock_aws
def test_list_customer_managed_policy_references_in_permission_set():
    """
    Tests listing customer managed policies including pagination.
    """
    client = boto3.client("sso-admin", region_name="us-east-1")
    permission_set_arn = create_permissionset(client)

    policy_name = "test-policy-"

    # attach 3 customer managed policies
    for idx in range(3):
        client.attach_customer_managed_policy_reference_to_permission_set(
            InstanceArn=DUMMY_INSTANCE_ARN,
            PermissionSetArn=permission_set_arn,
            CustomerManagedPolicyReference={"Name": f"{policy_name}{idx}"},
        )

    response = client.list_customer_managed_policy_references_in_permission_set(
        InstanceArn=DUMMY_INSTANCE_ARN,
        PermissionSetArn=permission_set_arn,
        MaxResults=2,
    )

    customer_managed_policy_names = []

    assert len(response["CustomerManagedPolicyReferences"]) == 2
    next_token = response["NextToken"]
    for name in response["CustomerManagedPolicyReferences"]:
        customer_managed_policy_names.append(name["Name"])

    response = client.list_customer_managed_policy_references_in_permission_set(
        InstanceArn=DUMMY_INSTANCE_ARN,
        PermissionSetArn=permission_set_arn,
        MaxResults=2,
        NextToken=next_token,
    )
    for name in response["CustomerManagedPolicyReferences"]:
        customer_managed_policy_names.append(name["Name"])

    assert len(response["CustomerManagedPolicyReferences"]) == 1

    # ensure the 3 unique customer managed policies were returned
    assert len(set(customer_managed_policy_names)) == 3


@mock_aws
def test_detach_customer_managed_policy_reference_from_permission_set():
    client = boto3.client("sso-admin", region_name="us-east-1")
    permission_set_arn = create_permissionset(client)

    # trying to detach a policy that doesn't exist yet
    with pytest.raises(ClientError) as e:
        client.detach_customer_managed_policy_reference_from_permission_set(
            InstanceArn=DUMMY_INSTANCE_ARN,
            PermissionSetArn=permission_set_arn,
            CustomerManagedPolicyReference={
                "Name": "test-policy",
            },
        )
    err = e.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert (
        err["Message"]
        == "Given managed policy with name: test-policy  and path / does not exist on PermissionSet"
    )

    # attach a policy
    client.attach_customer_managed_policy_reference_to_permission_set(
        InstanceArn=DUMMY_INSTANCE_ARN,
        PermissionSetArn=permission_set_arn,
        CustomerManagedPolicyReference={
            "Name": "test-policy",
            "Path": "/some-path/",
        },
    )

    # try to detach the policy but default path (should fail)
    with pytest.raises(ClientError) as e:
        client.detach_customer_managed_policy_reference_from_permission_set(
            InstanceArn=DUMMY_INSTANCE_ARN,
            PermissionSetArn=permission_set_arn,
            CustomerManagedPolicyReference={
                "Name": "test-policy",
            },
        )

    # detach the policy
    client.detach_customer_managed_policy_reference_from_permission_set(
        InstanceArn=DUMMY_INSTANCE_ARN,
        PermissionSetArn=permission_set_arn,
        CustomerManagedPolicyReference={
            "Name": "test-policy",
            "Path": "/some-path/",
        },
    )

    # ensure policy is detached
    response = client.list_customer_managed_policy_references_in_permission_set(
        InstanceArn=DUMMY_INSTANCE_ARN,
        PermissionSetArn=permission_set_arn,
    )

    assert len(response["CustomerManagedPolicyReferences"]) == 0
