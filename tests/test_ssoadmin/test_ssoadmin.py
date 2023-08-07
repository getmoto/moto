import datetime
from uuid import uuid4

import boto3
from botocore.exceptions import ClientError
import pytest

from moto import mock_ssoadmin

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_ssoadmin
def test_create_account_assignment():
    client = boto3.client("sso-admin", region_name="eu-west-1")
    target_id = "222222222222"
    permission_set_arn = (
        "arn:aws:sso:::permissionSet/ins-eeeeffffgggghhhh/ps-hhhhkkkkppppoooo"
    )
    principal_id = str(uuid4())

    resp = client.create_account_assignment(
        InstanceArn="arn:aws:sso:::instance/ins-aaaabbbbccccdddd",
        TargetId=target_id,
        TargetType="AWS_ACCOUNT",
        PermissionSetArn=permission_set_arn,
        PrincipalType="USER",
        PrincipalId=principal_id,
    )

    assert "AccountAssignmentCreationStatus" in resp

    status = resp["AccountAssignmentCreationStatus"]
    assert status["Status"] == "SUCCEEDED"
    assert "RequestId" in status
    assert "FailureReason" not in status
    assert status["TargetId"] == target_id
    assert status["TargetType"] == "AWS_ACCOUNT"
    assert status["PermissionSetArn"] == permission_set_arn
    assert status["PrincipalType"] == "USER"
    assert status["PrincipalId"] == principal_id


@mock_ssoadmin
def test_delete_account_assignment():
    client = boto3.client("sso-admin", region_name="eu-west-1")
    target_id = "222222222222"
    permission_set_arn = (
        "arn:aws:sso:::permissionSet/ins-eeeeffffgggghhhh/ps-hhhhkkkkppppoooo"
    )
    principal_id = str(uuid4())
    instance_arn = "arn:aws:sso:::instance/ins-aaaabbbbccccdddd"

    client.create_account_assignment(
        InstanceArn=instance_arn,
        TargetId=target_id,
        TargetType="AWS_ACCOUNT",
        PermissionSetArn=permission_set_arn,
        PrincipalType="USER",
        PrincipalId=principal_id,
    )

    resp = client.delete_account_assignment(
        InstanceArn=instance_arn,
        TargetId=target_id,
        TargetType="AWS_ACCOUNT",
        PermissionSetArn=permission_set_arn,
        PrincipalType="USER",
        PrincipalId=principal_id,
    )
    assert "AccountAssignmentDeletionStatus" in resp

    # Verify the correct response
    status = resp["AccountAssignmentDeletionStatus"]
    assert status["Status"] == "SUCCEEDED"
    assert "RequestId" in status
    assert "FailureReason" not in status
    assert status["TargetId"] == target_id
    assert status["TargetType"] == "AWS_ACCOUNT"
    assert status["PermissionSetArn"] == permission_set_arn
    assert status["PrincipalType"] == "USER"
    assert status["PrincipalId"] == principal_id
    assert isinstance(status["CreatedDate"], datetime.datetime)

    # Verify this account assignment can no longer be found
    resp = client.list_account_assignments(
        InstanceArn=instance_arn,
        AccountId=target_id,
        PermissionSetArn=permission_set_arn,
    )

    assert resp["AccountAssignments"] == []


@mock_ssoadmin
def test_delete_account_assignment_unknown():
    client = boto3.client("sso-admin", region_name="us-east-1")

    target_id = "222222222222"
    permission_set_arn = (
        "arn:aws:sso:::permissionSet/ins-eeeeffffgggghhhh/ps-hhhhkkkkppppoooo"
    )
    principal_id = str(uuid4())
    instance_arn = "arn:aws:sso:::instance/ins-aaaabbbbccccdddd"

    with pytest.raises(ClientError) as exc:
        client.delete_account_assignment(
            InstanceArn=instance_arn,
            TargetId=target_id,
            TargetType="AWS_ACCOUNT",
            PermissionSetArn=permission_set_arn,
            PrincipalType="USER",
            PrincipalId=principal_id,
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFound"


@mock_ssoadmin
def test_list_account_assignments():
    client = boto3.client("sso-admin", region_name="ap-southeast-1")

    target_id1 = "222222222222"
    target_id2 = "333333333333"
    permission_set_arn = (
        "arn:aws:sso:::permissionSet/ins-eeeeffffgggghhhh/ps-hhhhkkkkppppoooo"
    )
    principal_id = str(uuid4())
    instance_arn = "arn:aws:sso:::instance/ins-aaaabbbbccccdddd"

    resp = client.list_account_assignments(
        InstanceArn=instance_arn,
        AccountId=target_id1,
        PermissionSetArn=permission_set_arn,
    )

    assert resp["AccountAssignments"] == []

    client.create_account_assignment(
        InstanceArn=instance_arn,
        TargetId=target_id1,
        TargetType="AWS_ACCOUNT",
        PermissionSetArn=permission_set_arn,
        PrincipalType="USER",
        PrincipalId=principal_id,
    )

    resp = client.list_account_assignments(
        InstanceArn=instance_arn,
        AccountId=target_id1,
        PermissionSetArn=permission_set_arn,
    )

    assert resp["AccountAssignments"] == [
        {
            "AccountId": target_id1,
            "PermissionSetArn": permission_set_arn,
            "PrincipalType": "USER",
            "PrincipalId": principal_id,
        }
    ]

    client.create_account_assignment(
        InstanceArn=instance_arn,
        TargetId=target_id2,
        TargetType="AWS_ACCOUNT",
        PermissionSetArn=permission_set_arn,
        PrincipalType="USER",
        PrincipalId=principal_id,
    )

    resp = client.list_account_assignments(
        InstanceArn=instance_arn,
        AccountId=target_id2,
        PermissionSetArn=permission_set_arn,
    )

    assert resp["AccountAssignments"] == [
        {
            "AccountId": target_id2,
            "PermissionSetArn": permission_set_arn,
            "PrincipalType": "USER",
            "PrincipalId": principal_id,
        }
    ]


@mock_ssoadmin
def test_create_permission_set():
    client = boto3.client("sso-admin", region_name="ap-southeast-1")
    resp = client.create_permission_set(
        Name="test",
        Description="Test permission set",
        InstanceArn="arn:aws:sso:::instance/ins-aaaabbbbccccdddd",
        SessionDuration="PT1H",
        RelayState="https://console.aws.amazon.com/ec2",
    )
    assert "PermissionSet" in resp
    permission_set = resp["PermissionSet"]
    assert permission_set["Name"] == "test"
    assert "PermissionSetArn" in permission_set
    assert "Description" in permission_set
    assert "CreatedDate" in permission_set
    assert "SessionDuration" in permission_set
    assert "RelayState" in permission_set


@mock_ssoadmin
def test_update_permission_set():
    client = boto3.client("sso-admin", region_name="ap-southeast-1")
    resp = client.create_permission_set(
        Name="test",
        Description="Test permission set",
        InstanceArn="arn:aws:sso:::instance/ins-aaaabbbbccccdddd",
        SessionDuration="PT1H",
    )
    permission_set = resp["PermissionSet"]

    resp = client.update_permission_set(
        InstanceArn="arn:aws:sso:::instance/ins-aaaabbbbccccdddd",
        PermissionSetArn=permission_set["PermissionSetArn"],
        Description="New description",
        SessionDuration="PT2H",
        RelayState="https://console.aws.amazon.com/s3",
    )
    resp = client.describe_permission_set(
        InstanceArn="arn:aws:sso:::instance/ins-aaaabbbbccccdddd",
        PermissionSetArn=permission_set["PermissionSetArn"],
    )
    assert "PermissionSet" in resp
    permission_set = resp["PermissionSet"]
    assert permission_set["Name"] == "test"
    assert permission_set["Description"] == "New description"
    assert "CreatedDate" in permission_set
    assert permission_set["SessionDuration"] == "PT2H"
    assert permission_set["RelayState"] == "https://console.aws.amazon.com/s3"


@mock_ssoadmin
def test_update_permission_set_unknown():
    client = boto3.client("sso-admin", region_name="ap-southeast-1")

    with pytest.raises(ClientError) as exc:
        client.update_permission_set(
            InstanceArn="arn:aws:sso:::instance/ins-aaaabbbbccccdddd",
            PermissionSetArn=(
                "arn:aws:sso:::permissionSet/ins-eeeeffffgggghhhh/"
                "ps-hhhhkkkkppppoooo"
            ),
            Description="New description",
            SessionDuration="PT2H",
            RelayState="https://console.aws.amazon.com/s3",
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFound"


@mock_ssoadmin
def test_describe_permission_set():
    client = boto3.client("sso-admin", region_name="ap-southeast-1")
    resp = client.create_permission_set(
        Name="test",
        Description="Test permission set",
        InstanceArn="arn:aws:sso:::instance/ins-aaaabbbbccccdddd",
        SessionDuration="PT1H",
    )
    permission_set = resp["PermissionSet"]

    resp = client.describe_permission_set(
        InstanceArn="arn:aws:sso:::instance/ins-aaaabbbbccccdddd",
        PermissionSetArn=permission_set["PermissionSetArn"],
    )
    assert "PermissionSet" in resp
    permission_set = resp["PermissionSet"]
    assert permission_set["Name"] == "test"
    assert "PermissionSetArn" in permission_set
    assert "Description" in permission_set
    assert "CreatedDate" in permission_set
    assert "SessionDuration" in permission_set


@mock_ssoadmin
def test_describe_permission_set_unknown():
    client = boto3.client("sso-admin", region_name="ap-southeast-1")

    with pytest.raises(ClientError) as exc:
        client.describe_permission_set(
            InstanceArn="arn:aws:sso:::instance/ins-aaaabbbbccccdddd",
            PermissionSetArn="arn:aws:sso:::permissionSet/ins-eeeeffffgggghhhh/ps-hhhhkkkkppppoooo",
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFound"


@mock_ssoadmin
def test_delete_permission_set():
    client = boto3.client("sso-admin", region_name="ap-southeast-1")
    resp = client.create_permission_set(
        Name="test",
        Description="Test permission set",
        InstanceArn="arn:aws:sso:::instance/ins-aaaabbbbccccdddd",
        SessionDuration="PT1H",
    )
    permission_set = resp["PermissionSet"]
    resp = client.delete_permission_set(
        InstanceArn="arn:aws:sso:::instance/ins-aaaabbbbccccdddd",
        PermissionSetArn=permission_set["PermissionSetArn"],
    )
    with pytest.raises(ClientError) as exc:
        client.describe_permission_set(
            InstanceArn="arn:aws:sso:::instance/ins-aaaabbbbccccdddd",
            PermissionSetArn=permission_set["PermissionSetArn"],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFound"


@mock_ssoadmin
def test_delete_permission_set_unknown():
    client = boto3.client("sso-admin", region_name="ap-southeast-1")

    with pytest.raises(ClientError) as exc:
        client.delete_permission_set(
            InstanceArn="arn:aws:sso:::instance/ins-aaaabbbbccccdddd",
            PermissionSetArn="arn:aws:sso:::permissionSet/ins-eeeeffffgggghhhh/ps-hhhhkkkkppppoooo",
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFound"


@mock_ssoadmin
def test_list_permission_sets():
    client = boto3.client("sso-admin", region_name="ap-southeast-1")

    response = client.list_permission_sets(
        InstanceArn="arn:aws:sso:::instance/ins-aaaabbbbccccdddd",
    )
    assert "PermissionSets" in response
    permission_sets = response["PermissionSets"]
    assert not permission_sets

    for i in range(5):
        client.create_permission_set(
            Name="test" + str(i),
            Description="Test permission set " + str(i),
            InstanceArn="arn:aws:sso:::instance/ins-aaaabbbbccccdddd",
            SessionDuration="PT1H",
        )
    response = client.list_permission_sets(
        InstanceArn="arn:aws:sso:::instance/ins-aaaabbbbccccdddd",
    )
    assert "PermissionSets" in response
    permission_sets = response["PermissionSets"]
    assert len(permission_sets) == 5


@mock_ssoadmin
def test_list_permission_sets_pagination():
    client = boto3.client("sso-admin", region_name="ap-southeast-1")

    response = client.list_permission_sets(
        InstanceArn="arn:aws:sso:::instance/ins-aaaabbbbccccdddd",
    )
    assert "PermissionSets" in response
    permission_sets = response["PermissionSets"]
    assert not permission_sets

    for i in range(25):
        client.create_permission_set(
            Name="test" + str(i),
            Description="Test permission set " + str(i),
            InstanceArn="arn:aws:sso:::instance/ins-aaaabbbbccccdddd",
            SessionDuration="PT1H",
        )
    response = client.list_permission_sets(
        InstanceArn="arn:aws:sso:::instance/ins-aaaabbbbccccdddd",
    )
    assert "PermissionSets" in response
    assert "NextToken" not in response

    paginator = client.get_paginator("list_permission_sets")
    page_iterator = paginator.paginate(
        InstanceArn="arn:aws:sso:::instance/ins-aaaabbbbccccdddd", MaxResults=5
    )
    for page in page_iterator:
        assert len(page["PermissionSets"]) <= 5
