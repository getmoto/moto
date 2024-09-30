"""Unit tests for quicksight-supported APIs."""

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@pytest.mark.parametrize(
    "request_params",
    [
        {
            "Email": "fakeemail@example.com",
            "UserName": "tfacctestm9hpsr970z",
            "UserRole": "READER",
            "IdentityType": "QUICKSIGHT",
        },
        {
            "Email": "authoremail@example.com",
            "UserName": "authoremail@example.com",
            "UserRole": "AUTHOR",
            "IdentityType": "IAM",
        },
    ],
)
@mock_aws
def test_register_user__quicksight(request_params):
    client = boto3.client("quicksight", region_name="us-east-2")
    resp = client.register_user(
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
        Email=request_params["Email"],
        IdentityType=request_params["IdentityType"],
        UserName=request_params["UserName"],
        UserRole=request_params["UserRole"],
    )

    assert "UserInvitationUrl" in resp
    assert "User" in resp

    assert resp["User"]["Arn"] == (
        f"arn:aws:quicksight:us-east-2:{ACCOUNT_ID}:user/default/{request_params['UserName']}"
    )
    assert resp["User"]["UserName"] == request_params["UserName"]
    assert resp["User"]["Email"] == request_params["Email"]
    assert resp["User"]["Role"] == request_params["UserRole"]
    assert resp["User"]["IdentityType"] == request_params["IdentityType"]
    assert resp["User"]["Active"] is False


@pytest.mark.parametrize(
    "request_params",
    [
        {
            "Email": "fakeemail@example.com",
            "UserName": "tfacctestm9hpsr970z",
            "UserRole": "READER",
            "IdentityType": "QUICKSIGHT",
        },
        {
            "Email": "authoremail@example.com",
            "UserName": "authoremail@example.com",
            "UserRole": "AUTHOR",
            "IdentityType": "IAM",
        },
    ],
)
@mock_aws
def test_describe_user__quicksight(request_params):
    client = boto3.client("quicksight", region_name="us-east-1")
    client.register_user(
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
        Email=request_params["Email"],
        IdentityType=request_params["IdentityType"],
        UserName=request_params["UserName"],
        UserRole=request_params["UserRole"],
    )

    resp = client.describe_user(
        UserName=request_params["UserName"],
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
    )

    assert "User" in resp

    assert resp["User"]["Arn"] == (
        f"arn:aws:quicksight:us-east-1:{ACCOUNT_ID}:user/default/{request_params['UserName']}"
    )
    assert resp["User"]["UserName"] == request_params["UserName"]
    assert resp["User"]["Email"] == request_params["Email"]
    assert resp["User"]["Role"] == request_params["UserRole"]
    assert resp["User"]["IdentityType"] == request_params["IdentityType"]
    assert resp["User"]["Active"] is False


@pytest.mark.parametrize(
    "request_params",
    [
        {
            "Email": "fakeemail@example.com",
            "UserName": "tfacctestm9hpsr970z",
            "UserRole": "READER",
            "IdentityType": "QUICKSIGHT",
        },
        {
            "Email": "authoremail@example.com",
            "UserName": "authoremail@example.com",
            "UserRole": "AUTHOR",
            "IdentityType": "IAM",
        },
    ],
)
@mock_aws
def test_delete_user__quicksight(request_params):
    client = boto3.client("quicksight", region_name="us-east-2")
    client.register_user(
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
        Email=request_params["Email"],
        IdentityType=request_params["IdentityType"],
        UserName=request_params["UserName"],
        UserRole=request_params["UserRole"],
    )

    client.delete_user(
        UserName=request_params["UserName"],
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
    )

    with pytest.raises(ClientError) as exc:
        client.describe_user(
            UserName=request_params["UserName"],
            AwsAccountId=ACCOUNT_ID,
            Namespace="default",
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
    for i in range(2):
        client.register_user(
            AwsAccountId=ACCOUNT_ID,
            Namespace="default",
            Email=f"fakeemail{i}@example.com",
            IdentityType="QUICKSIGHT",
            UserName=f"fake{i}",
            UserRole="READER",
        )
    for i in range(2, 4):
        client.register_user(
            AwsAccountId=ACCOUNT_ID,
            Namespace="default",
            Email=f"fakeemail{i}@example.com",
            IdentityType="IAM",
            UserName=f"fakeemail{i}@example.com",
            UserRole="AUTHOR",
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
        "Arn": f"arn:aws:quicksight:us-east-2:{ACCOUNT_ID}:user/default/fakeemail3@example.com",
        "UserName": "fakeemail3@example.com",
        "Email": "fakeemail3@example.com",
        "Role": "AUTHOR",
        "IdentityType": "IAM",
        "Active": False,
    } in resp["UserList"]


@pytest.mark.parametrize(
    "request_params",
    [
        {
            "Email": "fakeemail@example.com",
            "UserName": "user.1",
            "UserRole": "READER",
            "IdentityType": "QUICKSIGHT",
            "GroupName": "group1",
        },
        {
            "Email": "authoremail@example.com",
            "UserName": "authoremail@example.com",
            "UserRole": "AUTHOR",
            "IdentityType": "IAM",
            "GroupName": "group.2",
        },
    ],
)
@mock_aws
def test_create_group_membership(request_params):
    client = boto3.client("quicksight", region_name="us-east-2")
    client.register_user(
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
        Email=request_params["Email"],
        IdentityType=request_params["IdentityType"],
        UserName=request_params["UserName"],
        UserRole=request_params["UserRole"],
    )
    client.create_group(
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
        GroupName=request_params["GroupName"],
    )

    resp = client.create_group_membership(
        MemberName=request_params["UserName"],
        GroupName=request_params["GroupName"],
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
    )

    assert resp["GroupMember"] == {
        "Arn": f"arn:aws:quicksight:us-east-2:{ACCOUNT_ID}:group/default/{request_params['GroupName']}/{request_params['UserName']}",
        "MemberName": request_params["UserName"],
    }
    assert resp["Status"] == 200


@pytest.mark.parametrize(
    "request_params",
    [
        {
            "Email": "fakeemail@example.com",
            "UserName": "user.1",
            "UserRole": "READER",
            "IdentityType": "QUICKSIGHT",
            "GroupName": "group1",
        },
        {
            "Email": "authoremail@example.com",
            "UserName": "authoremail@example.com",
            "UserRole": "AUTHOR",
            "IdentityType": "IAM",
            "GroupName": "group.2",
        },
    ],
)
@mock_aws
def test_describe_group_membership(request_params):
    client = boto3.client("quicksight", region_name="us-east-2")
    client.register_user(
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
        Email=request_params["Email"],
        IdentityType=request_params["IdentityType"],
        UserName=request_params["UserName"],
        UserRole=request_params["UserRole"],
    )
    client.create_group(
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
        GroupName=request_params["GroupName"],
    )

    client.create_group_membership(
        MemberName=request_params["UserName"],
        GroupName=request_params["GroupName"],
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
    )

    resp = client.describe_group_membership(
        MemberName=request_params["UserName"],
        GroupName=request_params["GroupName"],
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
    )

    assert resp["GroupMember"] == {
        "Arn": f"arn:aws:quicksight:us-east-2:{ACCOUNT_ID}:group/default/{request_params['GroupName']}/{request_params['UserName']}",
        "MemberName": request_params["UserName"],
    }
    assert resp["Status"] == 200


@mock_aws
def test_list_group_memberships():
    client = boto3.client("quicksight", region_name="us-east-2")
    for i in range(2):
        client.register_user(
            AwsAccountId=ACCOUNT_ID,
            Namespace="default",
            Email=f"fakeemail{i}@example.com",
            IdentityType="QUICKSIGHT",
            UserName=f"user{i}",
            UserRole="READER",
        )
    for i in range(2, 4):
        client.register_user(
            AwsAccountId=ACCOUNT_ID,
            Namespace="default",
            Email=f"fakeemail{i}@example.com",
            IdentityType="IAM",
            UserName=f"fakeemail{i}@example.com",
            UserRole="AUTHOR",
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
        MemberName="fakeemail2@example.com",
        GroupName="group1",
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
    )
    client.create_group_membership(
        MemberName="user1",
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
        "Arn": f"arn:aws:quicksight:us-east-2:{ACCOUNT_ID}:group/default/group1/fakeemail2@example.com",
        "MemberName": "fakeemail2@example.com",
    } in resp["GroupMemberList"]

    resp = client.list_group_memberships(
        GroupName="group2", AwsAccountId=ACCOUNT_ID, Namespace="default"
    )

    assert len(resp["GroupMemberList"]) == 1
    assert resp["Status"] == 200

    assert {
        "Arn": f"arn:aws:quicksight:us-east-2:{ACCOUNT_ID}:group/default/group2/user1",
        "MemberName": "user1",
    } in resp["GroupMemberList"]


@mock_aws
def test_list_group_memberships__after_deleting_user():
    client = boto3.client("quicksight", region_name="us-east-2")
    client.create_group(
        AwsAccountId=ACCOUNT_ID, Namespace="default", GroupName="group1"
    )
    for i in range(2):
        client.register_user(
            AwsAccountId=ACCOUNT_ID,
            Namespace="default",
            Email=f"fakeemail{i}@example.com",
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
    for i in range(2, 4):
        client.register_user(
            AwsAccountId=ACCOUNT_ID,
            Namespace="default",
            Email=f"fakeemail{i}@example.com",
            IdentityType="IAM",
            UserName=f"fakeemail{i}@example.com",
            UserRole="AUTHOR",
        )
        client.create_group_membership(
            MemberName=f"fakeemail{i}@example.com",
            GroupName="group1",
            AwsAccountId=ACCOUNT_ID,
            Namespace="default",
        )

    resp = client.list_group_memberships(
        GroupName="group1", AwsAccountId=ACCOUNT_ID, Namespace="default"
    )
    assert len(resp["GroupMemberList"]) == 4

    client.delete_user(UserName="user1", AwsAccountId=ACCOUNT_ID, Namespace="default")
    client.delete_user(
        UserName="fakeemail2@example.com",
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
    )

    resp = client.list_group_memberships(
        GroupName="group1", AwsAccountId=ACCOUNT_ID, Namespace="default"
    )
    assert len(resp["GroupMemberList"]) == 2
