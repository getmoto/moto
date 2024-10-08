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
def test_update_user(request_params):
    client = boto3.client("quicksight", region_name="us-west-2")
    client.register_user(
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
        Email=request_params["Email"],
        IdentityType=request_params["IdentityType"],
        UserName=request_params["UserName"],
        UserRole=request_params["UserRole"],
    )

    resp = client.update_user(
        UserName=request_params["UserName"],
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
        Email=request_params["Email"] + "_modified",
        Role="AUTHOR",
    )
    assert resp["User"]["Email"] == request_params["Email"] + "_modified"

    resp = client.describe_user(
        UserName=request_params["UserName"],
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
    )

    assert "User" in resp
    assert resp["User"]["Arn"] == (
        f"arn:aws:quicksight:us-west-2:{ACCOUNT_ID}:user/default/{request_params['UserName']}"
    )
    assert resp["User"]["UserName"] == request_params["UserName"]
    assert resp["User"]["Email"] == request_params["Email"] + "_modified"
    assert resp["User"]["Role"] == "AUTHOR"
    assert resp["User"]["IdentityType"] == request_params["IdentityType"]
    assert resp["User"]["Active"] is False


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


@mock_aws
def test_list_users__paginated():
    client = boto3.client("quicksight", region_name="us-east-2")
    for i in range(125):
        client.register_user(
            AwsAccountId=ACCOUNT_ID,
            Namespace="default",
            Email=f"fakeemail{i}@example.com",
            IdentityType="QUICKSIGHT",
            UserName=f"fake{i}",
            UserRole="READER",
        )

    # default pagesize is 100
    page1 = client.list_users(AwsAccountId=ACCOUNT_ID, Namespace="default")
    assert len(page1["UserList"]) == 100
    assert "NextToken" in page1

    # We can ask for a smaller pagesize
    page2 = client.list_users(
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
        MaxResults=15,
        NextToken=page1["NextToken"],
    )
    assert len(page2["UserList"]) == 15
    assert "NextToken" in page2

    # We could request all of them in one go
    all_users = client.list_users(
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
        MaxResults=1000,
    )
    length = len(all_users["UserList"])
    # We don't know exactly how much workspaces there are, because we are running multiple tests at the same time
    assert length >= 125


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
            "GroupName": "group@test",
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
            "GroupName": "group@test",
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


@mock_aws
def test_list_group_memberships__check_exceptions():
    client = boto3.client("quicksight", region_name="us-east-2")
    client.register_user(
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
        Email="fakeemail@example.com",
        IdentityType="QUICKSIGHT",
        UserName="user",
        UserRole="READER",
    )

    client.create_group(AwsAccountId=ACCOUNT_ID, Namespace="default", GroupName="group")

    client.create_group_membership(
        MemberName="user",
        GroupName="group",
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
    )

    # Test for user is member of group
    resp = client.describe_group_membership(
        MemberName="user",
        GroupName="group",
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
    )
    assert resp["Status"] == 200
    assert resp["GroupMember"] == {
        "Arn": f"arn:aws:quicksight:us-east-2:{ACCOUNT_ID}:group/default/group/user",
        "MemberName": "user",
    }

    # Test for user is not member of group
    with pytest.raises(ClientError) as exc:
        resp = client.describe_group_membership(
            MemberName="fake_user",
            GroupName="group",
            AwsAccountId=ACCOUNT_ID,
            Namespace="default",
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"

    # Test for non existing group
    with pytest.raises(ClientError) as exc:
        resp = client.describe_group_membership(
            MemberName="user",
            GroupName="fake_group",
            AwsAccountId=ACCOUNT_ID,
            Namespace="default",
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"


@mock_aws
def test_list_group_memberships__paginated():
    client = boto3.client("quicksight", region_name="us-east-2")
    client.create_group(
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
        GroupName="group",
    )
    for i in range(125):
        client.register_user(
            AwsAccountId=ACCOUNT_ID,
            Namespace="default",
            Email=f"authoremail{i}@example.com",
            IdentityType="QUICKSIGHT",
            UserName=f"user.{i}",
            UserRole="AUTHOR",
        )
        client.create_group_membership(
            MemberName=f"user.{i}",
            GroupName="group",
            AwsAccountId=ACCOUNT_ID,
            Namespace="default",
        )

    # default pagesize is 100
    page1 = client.list_group_memberships(
        GroupName="group", AwsAccountId=ACCOUNT_ID, Namespace="default"
    )
    assert len(page1["GroupMemberList"]) == 100
    assert "NextToken" in page1

    # We can ask for a smaller pagesize
    page2 = client.list_group_memberships(
        GroupName="group",
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
        MaxResults=15,
        NextToken=page1["NextToken"],
    )
    assert len(page2["GroupMemberList"]) == 15
    assert "NextToken" in page2

    # We could request all of them in one go
    all_users = client.list_group_memberships(
        GroupName="group",
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
        MaxResults=1000,
    )
    length = len(all_users["GroupMemberList"])
    # We don't know exactly how much workspaces there are, because we are running multiple tests at the same time
    assert length >= 125


@pytest.mark.parametrize(
    "request_params",
    [
        {
            "Email": "fakeemail@example.com",
            "UserName": "user.1",
            "UserRole": "READER",
            "IdentityType": "QUICKSIGHT",
            "GroupName1": "group1",
            "GroupName2": "group2",
            "GroupName3": "group3",
        },
        {
            "Email": "authoremail@example.com",
            "UserName": "authoremail@example.com",
            "UserRole": "AUTHOR",
            "IdentityType": "IAM",
            "GroupName1": "group1@test",
            "GroupName2": "group2@test",
            "GroupName3": "group3@test",
        },
    ],
)
@mock_aws
def test_list_user_groups(request_params):
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
        GroupName=request_params["GroupName1"],
    )
    client.create_group(
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
        GroupName=request_params["GroupName2"],
    )
    client.create_group(
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
        GroupName=request_params["GroupName3"],
    )
    client.create_group_membership(
        MemberName=request_params["UserName"],
        GroupName=request_params["GroupName1"],
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
    )
    client.create_group_membership(
        MemberName=request_params["UserName"],
        GroupName=request_params["GroupName2"],
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
    )

    resp = client.list_user_groups(
        UserName=request_params["UserName"],
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
    )

    assert resp["GroupList"] == [
        {
            "Arn": f"arn:aws:quicksight:us-east-2:{ACCOUNT_ID}:group/default/{request_params['GroupName1']}",
            "GroupName": request_params["GroupName1"],
            "PrincipalId": ACCOUNT_ID,
        },
        {
            "Arn": f"arn:aws:quicksight:us-east-2:{ACCOUNT_ID}:group/default/{request_params['GroupName2']}",
            "GroupName": request_params["GroupName2"],
            "PrincipalId": ACCOUNT_ID,
        },
    ]
    assert resp["Status"] == 200


@mock_aws
def test_list_user_groups__paginate():
    client = boto3.client("quicksight", region_name="us-east-2")
    client.register_user(
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
        Email="fakeemail@example.com",
        IdentityType="QUICKSIGHT",
        UserName="fake_user",
        UserRole="READER",
    )
    for i in range(125):
        client.create_group(
            AwsAccountId=ACCOUNT_ID,
            Namespace="default",
            GroupName=f"group{i}",
        )

        client.create_group_membership(
            MemberName="fake_user",
            GroupName=f"group{i}",
            AwsAccountId=ACCOUNT_ID,
            Namespace="default",
        )

    # default pagesize is 100
    page1 = client.list_user_groups(
        UserName="fake_user",
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
    )
    assert len(page1["GroupList"]) == 100
    assert "NextToken" in page1

    # We can ask for a smaller pagesize
    page2 = client.list_user_groups(
        UserName="fake_user",
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
        MaxResults=15,
        NextToken=page1["NextToken"],
    )
    assert len(page2["GroupList"]) == 15
    assert "NextToken" in page2

    # We could request all of them in one go
    all_users = client.list_user_groups(
        UserName="fake_user",
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
        MaxResults=1000,
    )
    length = len(all_users["GroupList"])
    # We don't know exactly how much workspaces there are, because we are running multiple tests at the same time
    assert length >= 125


@mock_aws
def test_list_users__diff_account_region():
    ACCOUNT_ID_2 = "998877665544"
    client_us = boto3.client("quicksight", region_name="us-east-2")
    client_eu = boto3.client("quicksight", region_name="eu-west-1")
    client_us.register_user(
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
        Email="fake_us_1@example.com",
        IdentityType="QUICKSIGHT",
        UserName="fake_us_1",
        UserRole="READER",
    )
    resp = client_us.register_user(
        AwsAccountId=ACCOUNT_ID_2,
        Namespace="default",
        Email="fake_us_2@example.com",
        IdentityType="QUICKSIGHT",
        UserName="fake_us_2",
        UserRole="AUTHOR",
    )
    client_eu.register_user(
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
        Email="fake_eu_1@example.com",
        IdentityType="IAM",
        UserName="fake_eu_1",
        UserRole="AUTHOR",
    )

    # Return Account 1, Region US
    resp = client_us.list_users(AwsAccountId=ACCOUNT_ID, Namespace="default")

    assert len(resp["UserList"]) == 1
    assert resp["Status"] == 200

    resp["UserList"][0].pop("PrincipalId")

    assert resp["UserList"][0] == {
        "Arn": f"arn:aws:quicksight:us-east-2:{ACCOUNT_ID}:user/default/fake_us_1",
        "UserName": "fake_us_1",
        "Email": "fake_us_1@example.com",
        "Role": "READER",
        "IdentityType": "QUICKSIGHT",
        "Active": False,
    }

    # Return Account 2, Region US
    resp = client_us.list_users(AwsAccountId=ACCOUNT_ID_2, Namespace="default")

    assert len(resp["UserList"]) == 1
    assert resp["Status"] == 200

    resp["UserList"][0].pop("PrincipalId")

    assert resp["UserList"][0] == {
        "Arn": f"arn:aws:quicksight:us-east-2:{ACCOUNT_ID_2}:user/default/fake_us_2",
        "UserName": "fake_us_2",
        "Email": "fake_us_2@example.com",
        "Role": "AUTHOR",
        "IdentityType": "QUICKSIGHT",
        "Active": False,
    }

    # Return Account 1, Region EU
    resp = client_eu.list_users(AwsAccountId=ACCOUNT_ID, Namespace="default")

    assert len(resp["UserList"]) == 1
    assert resp["Status"] == 200

    resp["UserList"][0].pop("PrincipalId")

    assert resp["UserList"][0] == {
        "Arn": f"arn:aws:quicksight:eu-west-1:{ACCOUNT_ID}:user/default/fake_eu_1",
        "UserName": "fake_eu_1",
        "Email": "fake_eu_1@example.com",
        "Role": "AUTHOR",
        "IdentityType": "IAM",
        "Active": False,
    }
