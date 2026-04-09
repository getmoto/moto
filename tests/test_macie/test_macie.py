import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws

ADMIN_ACCOUNT_ID = "111111111111"
MEMBER_ACCOUNT_ID = "222222222222"
REGION = "us-east-1"


@mock_aws
def test_get_macie_session():
    admin_client = boto3.client("macie2", region_name=REGION)

    response = admin_client.get_macie_session()
    assert response["status"] == "ENABLED"
    assert response["findingPublishingFrequency"] == "FIFTEEN_MINUTES"
    assert "createdAt" in response
    assert "updatedAt" in response
    assert "serviceRole" in response


@mock_aws
def test_enable_macie():
    admin_client = boto3.client("macie2", region_name=REGION)

    admin_client.disable_macie()

    response = admin_client.enable_macie(
        findingPublishingFrequency="ONE_HOUR", status="ENABLED"
    )
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    session = admin_client.get_macie_session()
    assert session["status"] == "ENABLED"
    assert session["findingPublishingFrequency"] == "ONE_HOUR"


@mock_aws
def test_get_macie_session_after_disable():
    admin_client = boto3.client("macie2", region_name=REGION)

    admin_client.disable_macie()

    with pytest.raises(ClientError) as exc:
        admin_client.get_macie_session()

    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"


@mock_aws
def test_create_invitations():
    admin_client = boto3.client("macie2", region_name=REGION)

    response = admin_client.create_invitations(accountIds=[MEMBER_ACCOUNT_ID])
    assert response["unprocessedAccounts"] == []


@mock_aws
def test_list_invitations():
    admin_client = boto3.client("macie2", region_name=REGION)

    admin_client.create_invitations(accountIds=[MEMBER_ACCOUNT_ID])

    response = admin_client.list_invitations()
    assert len(response["invitations"]) == 1
    assert response["invitations"][0]["accountId"] == MEMBER_ACCOUNT_ID


@mock_aws
def test_decline_invitations():
    sts = boto3.client("sts", region_name=REGION)
    member_identity = sts.assume_role(
        RoleArn=f"arn:aws:iam::{MEMBER_ACCOUNT_ID}:role/my-role",
        RoleSessionName="test-session",
    )["Credentials"]

    admin_client = boto3.client("macie2", region_name=REGION)
    member_client = boto3.client(
        "macie2",
        region_name=REGION,
        aws_access_key_id=member_identity["AccessKeyId"],
        aws_secret_access_key=member_identity["SecretAccessKey"],
        aws_session_token=member_identity["SessionToken"],
    )

    admin_client.create_invitations(accountIds=[MEMBER_ACCOUNT_ID])

    response = member_client.decline_invitations(accountIds=[MEMBER_ACCOUNT_ID])
    assert response["unprocessedAccounts"] == []
    assert len(admin_client.list_invitations()["invitations"]) == 0


@mock_aws
def test_list_members():
    sts = boto3.client("sts", region_name=REGION)
    member_identity = sts.assume_role(
        RoleArn=f"arn:aws:iam::{MEMBER_ACCOUNT_ID}:role/my-role",
        RoleSessionName="test-session",
    )["Credentials"]

    admin_client = boto3.client("macie2", region_name=REGION)
    member_client = boto3.client(
        "macie2",
        region_name=REGION,
        aws_access_key_id=member_identity["AccessKeyId"],
        aws_secret_access_key=member_identity["SecretAccessKey"],
        aws_session_token=member_identity["SessionToken"],
    )

    admin_client.create_invitations(accountIds=[MEMBER_ACCOUNT_ID])
    invitation_id = admin_client.list_invitations()["invitations"][0]["invitationId"]
    member_client.accept_invitation(
        administratorAccountId=ADMIN_ACCOUNT_ID, invitationId=invitation_id
    )

    response = admin_client.list_members()
    assert len(response["members"]) == 1
    assert response["members"][0]["accountId"] == MEMBER_ACCOUNT_ID


@mock_aws
def test_get_administrator_account():
    sts = boto3.client("sts", region_name=REGION)
    member_identity = sts.assume_role(
        RoleArn=f"arn:aws:iam::{MEMBER_ACCOUNT_ID}:role/my-role",
        RoleSessionName="test-session",
    )["Credentials"]

    admin_client = boto3.client("macie2", region_name=REGION)
    member_client = boto3.client(
        "macie2",
        region_name=REGION,
        aws_access_key_id=member_identity["AccessKeyId"],
        aws_secret_access_key=member_identity["SecretAccessKey"],
        aws_session_token=member_identity["SessionToken"],
    )

    admin_client.create_invitations(accountIds=[MEMBER_ACCOUNT_ID])
    invitation_id = admin_client.list_invitations()["invitations"][0]["invitationId"]
    member_client.accept_invitation(
        administratorAccountId=ADMIN_ACCOUNT_ID, invitationId=invitation_id
    )

    response = member_client.get_administrator_account()
    assert response["administrator"]["accountId"] == ADMIN_ACCOUNT_ID


@mock_aws
def test_delete_member():
    sts = boto3.client("sts", region_name=REGION)
    member_identity = sts.assume_role(
        RoleArn=f"arn:aws:iam::{MEMBER_ACCOUNT_ID}:role/my-role",
        RoleSessionName="test-session",
    )["Credentials"]

    admin_client = boto3.client("macie2", region_name=REGION)
    member_client = boto3.client(
        "macie2",
        region_name=REGION,
        aws_access_key_id=member_identity["AccessKeyId"],
        aws_secret_access_key=member_identity["SecretAccessKey"],
        aws_session_token=member_identity["SessionToken"],
    )

    admin_client.create_invitations(accountIds=[MEMBER_ACCOUNT_ID])
    invitation_id = admin_client.list_invitations()["invitations"][0]["invitationId"]
    member_client.accept_invitation(
        administratorAccountId=ADMIN_ACCOUNT_ID, invitationId=invitation_id
    )

    response = admin_client.delete_member(id=MEMBER_ACCOUNT_ID)
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert len(admin_client.list_members()["members"]) == 0


@mock_aws
def test_delete_nonexistent_member():
    admin_client = boto3.client("macie2", region_name=REGION)

    with pytest.raises(ClientError) as exc:
        admin_client.delete_member(id="999999999999")

    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"


@mock_aws
def test_disable_macie():
    admin_client = boto3.client("macie2", region_name=REGION)

    admin_client.create_invitations(accountIds=[MEMBER_ACCOUNT_ID])

    response = admin_client.disable_macie()
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert len(admin_client.list_invitations()["invitations"]) == 0


@mock_aws
def test_enable_and_list_organization_admin_account():
    client = boto3.client("macie2", region_name=REGION)
    admin_to_set = "999988887777"

    response = client.list_organization_admin_accounts()
    assert response["adminAccounts"] == []

    client.enable_organization_admin_account(adminAccountId=admin_to_set)

    response = client.list_organization_admin_accounts()
    assert len(response["adminAccounts"]) == 1
    assert response["adminAccounts"][0]["accountId"] == admin_to_set
    assert response["adminAccounts"][0]["status"] == "ENABLED"


@mock_aws
def test_disassociate_member():
    sts = boto3.client("sts", region_name=REGION)
    member_identity = sts.assume_role(
        RoleArn=f"arn:aws:iam::{MEMBER_ACCOUNT_ID}:role/my-role",
        RoleSessionName="test-session",
    )["Credentials"]

    admin_client = boto3.client("macie2", region_name=REGION)
    member_client = boto3.client(
        "macie2",
        region_name=REGION,
        aws_access_key_id=member_identity["AccessKeyId"],
        aws_secret_access_key=member_identity["SecretAccessKey"],
        aws_session_token=member_identity["SessionToken"],
    )

    admin_client.create_invitations(accountIds=[MEMBER_ACCOUNT_ID])
    invitation_id = admin_client.list_invitations()["invitations"][0]["invitationId"]

    member_client.accept_invitation(
        administratorAccountId=ADMIN_ACCOUNT_ID, invitationId=invitation_id
    )

    assert len(admin_client.list_members()["members"]) == 1

    response = admin_client.disassociate_member(id=MEMBER_ACCOUNT_ID)
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    assert len(admin_client.list_members()["members"]) == 0

    admin_response = member_client.get_administrator_account()
    assert "administrator" not in admin_response
