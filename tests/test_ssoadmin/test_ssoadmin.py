import boto3
import datetime
import pytest
import sure  # noqa # pylint: disable=unused-import

from botocore.exceptions import ClientError
from moto import mock_ssoadmin
from uuid import uuid4

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

    resp.should.have.key("AccountAssignmentCreationStatus")

    status = resp["AccountAssignmentCreationStatus"]
    status.should.have.key("Status").equals("SUCCEEDED")
    status.should.have.key("RequestId")
    status.shouldnt.have.key("FailureReason")
    status.should.have.key("TargetId").equals(target_id)
    status.should.have.key("TargetType").equals("AWS_ACCOUNT")
    status.should.have.key("PermissionSetArn").equals(permission_set_arn)
    status.should.have.key("PrincipalType").equals("USER")
    status.should.have.key("PrincipalId").equals(principal_id)


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
    resp.should.have.key("AccountAssignmentDeletionStatus")

    # Verify the correct response
    status = resp["AccountAssignmentDeletionStatus"]
    status.should.have.key("Status").equals("SUCCEEDED")
    status.should.have.key("RequestId")
    status.shouldnt.have.key("FailureReason")
    status.should.have.key("TargetId").equals(target_id)
    status.should.have.key("TargetType").equals("AWS_ACCOUNT")
    status.should.have.key("PermissionSetArn").equals(permission_set_arn)
    status.should.have.key("PrincipalType").equals("USER")
    status.should.have.key("PrincipalId").equals(principal_id)
    status.should.have.key("CreatedDate").should.be.a(datetime.datetime)

    # Verify this account assignment can no longer be found
    resp = client.list_account_assignments(
        InstanceArn=instance_arn,
        AccountId=target_id,
        PermissionSetArn=permission_set_arn,
    )

    resp.should.have.key("AccountAssignments").equals([])


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
    err["Code"].should.equal("ResourceNotFound")


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

    resp.should.have.key("AccountAssignments").equals([])

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

    resp.should.have.key("AccountAssignments").equals(
        [
            {
                "AccountId": target_id1,
                "PermissionSetArn": permission_set_arn,
                "PrincipalType": "USER",
                "PrincipalId": principal_id,
            }
        ]
    )

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

    resp.should.have.key("AccountAssignments").equals(
        [
            {
                "AccountId": target_id2,
                "PermissionSetArn": permission_set_arn,
                "PrincipalType": "USER",
                "PrincipalId": principal_id,
            }
        ]
    )
