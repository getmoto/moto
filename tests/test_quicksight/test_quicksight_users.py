"""Unit tests for quicksight-supported APIs."""

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_aws
def test_register_user__quicksight():
    client = boto3.client("quicksight", region_name="us-east-2")
    resp = client.register_user(
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
        Email="fakeemail@example.com",
        IdentityType="QUICKSIGHT",
        UserName="tfacctestm9hpsr970z",
        UserRole="READER",
    )

    assert "UserInvitationUrl" in resp
    assert "User" in resp

    assert resp["User"]["Arn"] == (
        f"arn:aws:quicksight:us-east-2:{ACCOUNT_ID}:user/default/tfacctestm9hpsr970z"
    )
    assert resp["User"]["UserName"] == "tfacctestm9hpsr970z"
    assert resp["User"]["Email"] == "fakeemail@example.com"
    assert resp["User"]["Role"] == "READER"
    assert resp["User"]["IdentityType"] == "QUICKSIGHT"
    assert resp["User"]["Active"] is False


@mock_aws
def test_describe_user__quicksight():
    client = boto3.client("quicksight", region_name="us-east-1")
    client.register_user(
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
        Email="fakeemail@example.com",
        IdentityType="QUICKSIGHT",
        UserName="tfacctestm9hpsr970z",
        UserRole="READER",
    )

    resp = client.describe_user(
        UserName="tfacctestm9hpsr970z", AwsAccountId=ACCOUNT_ID, Namespace="default"
    )

    assert "User" in resp

    assert resp["User"]["Arn"] == (
        f"arn:aws:quicksight:us-east-1:{ACCOUNT_ID}:user/default/tfacctestm9hpsr970z"
    )
    assert resp["User"]["UserName"] == "tfacctestm9hpsr970z"
    assert resp["User"]["Email"] == "fakeemail@example.com"
    assert resp["User"]["Role"] == "READER"
    assert resp["User"]["IdentityType"] == "QUICKSIGHT"
    assert resp["User"]["Active"] is False


@mock_aws
def test_delete_user__quicksight():
    client = boto3.client("quicksight", region_name="us-east-2")
    client.register_user(
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
        Email="fakeemail@example.com",
        IdentityType="QUICKSIGHT",
        UserName="tfacctestm9hpsr970z",
        UserRole="READER",
    )

    client.delete_user(
        UserName="tfacctestm9hpsr970z", AwsAccountId=ACCOUNT_ID, Namespace="default"
    )

    with pytest.raises(ClientError) as exc:
        client.describe_user(
            UserName="tfacctestm9hpsr970z", AwsAccountId=ACCOUNT_ID, Namespace="default"
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"


@mock_aws
def test_list_users__initial():
    client = boto3.client("quicksight", region_name="us-east-2")
    resp = client.list_users(AwsAccountId=ACCOUNT_ID, Namespace="default")

    assert resp["UserList"] == []
    assert resp["Status"] == 200


@mock_aws
def test_list_users():
    client = boto3.client("quicksight", region_name="us-east-2")
    for i in range(4):
        client.register_user(
            AwsAccountId=ACCOUNT_ID,
            Namespace="default",
            Email=f"fakeemail{i}@example.com",
            IdentityType="QUICKSIGHT",
            UserName=f"fake{i}",
            UserRole="READER",
        )

    resp = client.list_users(AwsAccountId=ACCOUNT_ID, Namespace="default")

    assert len(resp["UserList"]) == 4
    assert resp["Status"] == 200
    for user in resp["UserList"]:
        user.pop("PrincipalId")

    assert {
        "Arn": f"arn:aws:quicksight:us-east-2:{ACCOUNT_ID}:user/default/fake0",
        "UserName": "fake0",
        "Email": "fakeemail0@example.com",
        "Role": "READER",
        "IdentityType": "QUICKSIGHT",
        "Active": False,
    } in resp["UserList"]

    assert {
        "Arn": f"arn:aws:quicksight:us-east-2:{ACCOUNT_ID}:user/default/fake3",
        "UserName": "fake3",
        "Email": "fakeemail3@example.com",
        "Role": "READER",
        "IdentityType": "QUICKSIGHT",
        "Active": False,
    } in resp["UserList"]


@mock_aws
def test_create_group_membership():
    client = boto3.client("quicksight", region_name="us-east-2")
    client.register_user(
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
        Email="fakeemail@example.com",
        IdentityType="QUICKSIGHT",
        UserName="user.1",
        UserRole="READER",
    )
    client.create_group(
        AwsAccountId=ACCOUNT_ID, Namespace="default", GroupName="group1"
    )

    resp = client.create_group_membership(
        MemberName="user.1",
        GroupName="group1",
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
    )

    assert resp["GroupMember"] == {
        "Arn": f"arn:aws:quicksight:us-east-2:{ACCOUNT_ID}:group/default/group1/user.1",
        "MemberName": "user.1",
    }
    assert resp["Status"] == 200


@mock_aws
def test_describe_group_membership():
    client = boto3.client("quicksight", region_name="us-east-2")
    client.register_user(
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
        Email="fakeemail@example.com",
        IdentityType="QUICKSIGHT",
        UserName="user1",
        UserRole="READER",
    )
    client.create_group(
        AwsAccountId=ACCOUNT_ID, Namespace="default", GroupName="group1"
    )

    client.create_group_membership(
        MemberName="user1",
        GroupName="group1",
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
    )

    resp = client.describe_group_membership(
        MemberName="user1",
        GroupName="group1",
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
    )

    assert resp["GroupMember"] == {
        "Arn": f"arn:aws:quicksight:us-east-2:{ACCOUNT_ID}:group/default/group1/user1",
        "MemberName": "user1",
    }
    assert resp["Status"] == 200


@mock_aws
def test_list_group_memberships():
    client = boto3.client("quicksight", region_name="us-east-2")
    for i in range(3):
        client.register_user(
            AwsAccountId=ACCOUNT_ID,
            Namespace="default",
            Email="fakeemail@example.com",
            IdentityType="QUICKSIGHT",
            UserName=f"user{i}",
            UserRole="READER",
        )
    client.create_group(
        AwsAccountId=ACCOUNT_ID, Namespace="default", GroupName="group1"
    )
    client.create_group(
        AwsAccountId=ACCOUNT_ID, Namespace="default", GroupName="group2"
    )

    client.create_group_membership(
        MemberName="user0",
        GroupName="group1",
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
    )
    client.create_group_membership(
        MemberName="user1",
        GroupName="group1",
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
    )
    client.create_group_membership(
        MemberName="user2",
        GroupName="group2",
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
    )

    resp = client.list_group_memberships(
        GroupName="group1", AwsAccountId=ACCOUNT_ID, Namespace="default"
    )

    assert len(resp["GroupMemberList"]) == 2
    assert resp["Status"] == 200

    assert {
        "Arn": f"arn:aws:quicksight:us-east-2:{ACCOUNT_ID}:group/default/group1/user0",
        "MemberName": "user0",
    } in resp["GroupMemberList"]
    assert {
        "Arn": f"arn:aws:quicksight:us-east-2:{ACCOUNT_ID}:group/default/group1/user1",
        "MemberName": "user1",
    } in resp["GroupMemberList"]


@mock_aws
def test_list_group_memberships__after_deleting_user():
    client = boto3.client("quicksight", region_name="us-east-2")
    client.create_group(
        AwsAccountId=ACCOUNT_ID, Namespace="default", GroupName="group1"
    )
    for i in range(3):
        client.register_user(
            AwsAccountId=ACCOUNT_ID,
            Namespace="default",
            Email="fakeemail@example.com",
            IdentityType="QUICKSIGHT",
            UserName=f"user{i}",
            UserRole="READER",
        )
        client.create_group_membership(
            MemberName=f"user{i}",
            GroupName="group1",
            AwsAccountId=ACCOUNT_ID,
            Namespace="default",
        )

    resp = client.list_group_memberships(
        GroupName="group1", AwsAccountId=ACCOUNT_ID, Namespace="default"
    )
    assert len(resp["GroupMemberList"]) == 3

    client.delete_user(UserName="user1", AwsAccountId=ACCOUNT_ID, Namespace="default")

    resp = client.list_group_memberships(
        GroupName="group1", AwsAccountId=ACCOUNT_ID, Namespace="default"
    )
    assert len(resp["GroupMemberList"]) == 2
