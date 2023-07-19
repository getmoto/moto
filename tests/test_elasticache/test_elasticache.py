import boto3
import pytest

from botocore.exceptions import ClientError
from moto import mock_elasticache
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_elasticache
def test_create_user_no_password_required():
    client = boto3.client("elasticache", region_name="ap-southeast-1")
    user_id = "user1"
    resp = client.create_user(
        UserId=user_id,
        UserName="User1",
        Engine="Redis",
        AccessString="on ~* +@all",
        NoPasswordRequired=True,
    )

    assert resp["UserId"] == user_id
    assert resp["UserName"] == "User1"
    assert resp["Status"] == "active"
    assert resp["Engine"] == "Redis"
    assert resp["MinimumEngineVersion"] == "6.0"
    assert resp["AccessString"] == "on ~* +@all"
    assert resp["UserGroupIds"] == []
    assert resp["Authentication"]["Type"] == "no-password"
    assert "PasswordCount" not in resp["Authentication"]
    assert (
        resp["ARN"] == f"arn:aws:elasticache:ap-southeast-1:{ACCOUNT_ID}:user:{user_id}"
    )


@mock_elasticache
def test_create_user_with_password_too_short():
    client = boto3.client("elasticache", region_name="ap-southeast-1")
    user_id = "user1"
    with pytest.raises(ClientError) as exc:
        client.create_user(
            UserId=user_id,
            UserName="User1",
            Engine="Redis",
            AccessString="on ~* +@all",
            Passwords=["mysecretpass"],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert err["Message"] == "Passwords length must be between 16-128 characters."


@mock_elasticache
def test_create_user_with_password():
    client = boto3.client("elasticache", region_name="ap-southeast-1")
    user_id = "user1"
    resp = client.create_user(
        UserId=user_id,
        UserName="User1",
        Engine="Redis",
        AccessString="on ~* +@all",
        Passwords=["mysecretpassthatsverylong"],
    )

    assert resp["UserId"] == user_id
    assert resp["UserName"] == "User1"
    assert resp["Status"] == "active"
    assert resp["Engine"] == "Redis"
    assert resp["MinimumEngineVersion"] == "6.0"
    assert resp["AccessString"] == "on ~* +@all"
    assert resp["UserGroupIds"] == []
    assert resp["Authentication"]["Type"] == "password"
    assert resp["Authentication"]["PasswordCount"] == 1
    assert (
        resp["ARN"] == f"arn:aws:elasticache:ap-southeast-1:{ACCOUNT_ID}:user:{user_id}"
    )


@mock_elasticache
def test_create_user_without_password():
    client = boto3.client("elasticache", region_name="ap-southeast-1")
    with pytest.raises(ClientError) as exc:
        client.create_user(
            UserId="user1", UserName="User1", Engine="Redis", AccessString="?"
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert (
        err["Message"]
        == "No password was provided. If you want to create/update the user without password, please use the NoPasswordRequired flag."
    )


@mock_elasticache
def test_create_user_twice():
    client = boto3.client("elasticache", region_name="ap-southeast-1")
    user_id = "user1"
    client.create_user(
        UserId=user_id,
        UserName="User1",
        Engine="Redis",
        AccessString="on ~* +@all",
        Passwords=["mysecretpassthatsverylong"],
    )

    with pytest.raises(ClientError) as exc:
        client.create_user(
            UserId=user_id,
            UserName="User1",
            Engine="Redis",
            AccessString="on ~* +@all",
            Passwords=["mysecretpassthatsverylong"],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "UserAlreadyExists"
    assert err["Message"] == "User user1 already exists."


@mock_elasticache
def test_delete_user_unknown():
    client = boto3.client("elasticache", region_name="ap-southeast-1")
    with pytest.raises(ClientError) as exc:
        client.delete_user(UserId="unknown")
    err = exc.value.response["Error"]
    assert err["Code"] == "UserNotFound"
    assert err["Message"] == "User unknown not found."


@mock_elasticache
def test_delete_user():
    client = boto3.client("elasticache", region_name="ap-southeast-1")

    client.create_user(
        UserId="user1",
        UserName="User1",
        Engine="Redis",
        AccessString="on ~* +@all",
        Passwords=["mysecretpassthatsverylong"],
    )

    client.delete_user(UserId="user1")

    # Initial status is 'deleting'
    resp = client.describe_users(UserId="user1")
    assert resp["Users"][0]["Status"] == "deleting"

    # User is only deleted after some time
    with pytest.raises(ClientError) as exc:
        client.describe_users(UserId="unknown")
    assert exc.value.response["Error"]["Code"] == "UserNotFound"


@mock_elasticache
def test_describe_users_initial():
    client = boto3.client("elasticache", region_name="us-east-2")
    resp = client.describe_users()

    assert len(resp["Users"]) == 1
    assert resp["Users"][0] == {
        "UserId": "default",
        "UserName": "default",
        "Status": "active",
        "Engine": "redis",
        "MinimumEngineVersion": "6.0",
        "AccessString": "on ~* +@all",
        "UserGroupIds": [],
        "Authentication": {"Type": "no-password"},
        "ARN": f"arn:aws:elasticache:us-east-2:{ACCOUNT_ID}:user:default",
    }


@mock_elasticache
def test_describe_users():
    client = boto3.client("elasticache", region_name="ap-southeast-1")

    client.create_user(
        UserId="user1",
        UserName="User1",
        Engine="Redis",
        AccessString="on ~* +@all",
        Passwords=["mysecretpassthatsverylong"],
    )

    resp = client.describe_users()

    assert len(resp["Users"]) == 2
    assert {
        "UserId": "user1",
        "UserName": "User1",
        "Status": "active",
        "Engine": "Redis",
        "MinimumEngineVersion": "6.0",
        "AccessString": "on ~* +@all",
        "UserGroupIds": [],
        "Authentication": {"Type": "password", "PasswordCount": 1},
        "ARN": f"arn:aws:elasticache:ap-southeast-1:{ACCOUNT_ID}:user:user1",
    } in resp["Users"]


@mock_elasticache
def test_describe_users_unknown_userid():
    client = boto3.client("elasticache", region_name="ap-southeast-1")

    with pytest.raises(ClientError) as exc:
        client.describe_users(UserId="unknown")
    err = exc.value.response["Error"]
    assert err["Code"] == "UserNotFound"
    assert err["Message"] == "User unknown not found."
