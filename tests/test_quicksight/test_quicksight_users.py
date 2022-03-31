"""Unit tests for quicksight-supported APIs."""
import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import

from botocore.exceptions import ClientError
from moto import mock_quicksight
from moto.core import ACCOUNT_ID

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_quicksight
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

    resp.should.have.key("UserInvitationUrl")
    resp.should.have.key("User")

    resp["User"].should.have.key("Arn").equals(
        f"arn:aws:quicksight:us-east-2:{ACCOUNT_ID}:user/default/tfacctestm9hpsr970z"
    )
    resp["User"].should.have.key("UserName").equals("tfacctestm9hpsr970z")
    resp["User"].should.have.key("Email").equals("fakeemail@example.com")
    resp["User"].should.have.key("Role").equals("READER")
    resp["User"].should.have.key("IdentityType").equals("QUICKSIGHT")
    resp["User"].should.have.key("Active").equals(False)


@mock_quicksight
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

    resp.should.have.key("User")

    resp["User"].should.have.key("Arn").equals(
        f"arn:aws:quicksight:us-east-1:{ACCOUNT_ID}:user/default/tfacctestm9hpsr970z"
    )
    resp["User"].should.have.key("UserName").equals("tfacctestm9hpsr970z")
    resp["User"].should.have.key("Email").equals("fakeemail@example.com")
    resp["User"].should.have.key("Role").equals("READER")
    resp["User"].should.have.key("IdentityType").equals("QUICKSIGHT")
    resp["User"].should.have.key("Active").equals(False)


@mock_quicksight
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
    err["Code"].should.equal("ResourceNotFoundException")


@mock_quicksight
def test_list_users__initial():
    client = boto3.client("quicksight", region_name="us-east-2")
    resp = client.list_users(AwsAccountId=ACCOUNT_ID, Namespace="default")

    resp.should.have.key("UserList").equals([])
    resp.should.have.key("Status").equals(200)


@mock_quicksight
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

    resp.should.have.key("UserList").length_of(4)
    resp.should.have.key("Status").equals(200)

    resp["UserList"].should.contain(
        {
            "Arn": f"arn:aws:quicksight:us-east-2:{ACCOUNT_ID}:user/default/fake0",
            "UserName": "fake0",
            "Email": "fakeemail0@example.com",
            "Role": "READER",
            "IdentityType": "QUICKSIGHT",
            "Active": False,
        }
    )

    resp["UserList"].should.contain(
        {
            "Arn": f"arn:aws:quicksight:us-east-2:{ACCOUNT_ID}:user/default/fake3",
            "UserName": "fake3",
            "Email": "fakeemail3@example.com",
            "Role": "READER",
            "IdentityType": "QUICKSIGHT",
            "Active": False,
        }
    )


@mock_quicksight
def test_create_group_membership():
    client = boto3.client("quicksight", region_name="us-east-2")
    client.register_user(
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
        Email=f"fakeemail@example.com",
        IdentityType="QUICKSIGHT",
        UserName="user1",
        UserRole="READER",
    )
    client.create_group(
        AwsAccountId=ACCOUNT_ID, Namespace="default", GroupName="group1"
    )

    resp = client.create_group_membership(
        MemberName="user1",
        GroupName="group1",
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
    )

    resp.should.have.key("GroupMember").equals(
        {
            "Arn": f"arn:aws:quicksight:us-east-2:{ACCOUNT_ID}:group/default/group1/user1",
            "MemberName": "user1",
        }
    )
    resp.should.have.key("Status").equals(200)


@mock_quicksight
def test_describe_group_membership():
    client = boto3.client("quicksight", region_name="us-east-2")
    client.register_user(
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
        Email=f"fakeemail@example.com",
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

    resp.should.have.key("GroupMember").equals(
        {
            "Arn": f"arn:aws:quicksight:us-east-2:{ACCOUNT_ID}:group/default/group1/user1",
            "MemberName": "user1",
        }
    )
    resp.should.have.key("Status").equals(200)


@mock_quicksight
def test_list_group_memberships():
    client = boto3.client("quicksight", region_name="us-east-2")
    for i in range(3):
        client.register_user(
            AwsAccountId=ACCOUNT_ID,
            Namespace="default",
            Email=f"fakeemail@example.com",
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

    resp.should.have.key("GroupMemberList").length_of(2)
    resp.should.have.key("Status").equals(200)

    resp["GroupMemberList"].should.contain(
        {
            "Arn": f"arn:aws:quicksight:us-east-2:{ACCOUNT_ID}:group/default/group1/user0",
            "MemberName": "user0",
        }
    )
    resp["GroupMemberList"].should.contain(
        {
            "Arn": f"arn:aws:quicksight:us-east-2:{ACCOUNT_ID}:group/default/group1/user1",
            "MemberName": "user1",
        }
    )


@mock_quicksight
def test_list_group_memberships__after_deleting_user():
    client = boto3.client("quicksight", region_name="us-east-2")
    client.create_group(
        AwsAccountId=ACCOUNT_ID, Namespace="default", GroupName="group1"
    )
    for i in range(3):
        client.register_user(
            AwsAccountId=ACCOUNT_ID,
            Namespace="default",
            Email=f"fakeemail@example.com",
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
    resp.should.have.key("GroupMemberList").length_of(3)

    client.delete_user(UserName="user1", AwsAccountId=ACCOUNT_ID, Namespace="default")

    resp = client.list_group_memberships(
        GroupName="group1", AwsAccountId=ACCOUNT_ID, Namespace="default"
    )
    resp.should.have.key("GroupMemberList").length_of(2)
