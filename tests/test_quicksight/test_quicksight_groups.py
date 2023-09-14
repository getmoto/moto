"""Unit tests for quicksight-supported APIs."""
import boto3
from botocore.exceptions import ClientError
import pytest

from moto import mock_quicksight
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_quicksight
def test_create_group():
    client = boto3.client("quicksight", region_name="us-west-2")
    resp = client.create_group(
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
        GroupName="mygroup",
        Description="my new fancy group",
    )

    assert "Group" in resp

    assert resp["Group"]["Arn"] == (
        f"arn:aws:quicksight:us-west-2:{ACCOUNT_ID}:group/default/mygroup"
    )
    assert resp["Group"]["GroupName"] == "mygroup"
    assert resp["Group"]["Description"] == "my new fancy group"
    assert resp["Group"]["PrincipalId"] == f"{ACCOUNT_ID}"


@mock_quicksight
def test_describe_group():
    client = boto3.client("quicksight", region_name="us-west-2")
    client.create_group(
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
        GroupName="mygroup",
        Description="my new fancy group",
    )

    resp = client.describe_group(
        GroupName="mygroup", AwsAccountId=ACCOUNT_ID, Namespace="default"
    )

    assert "Group" in resp

    assert resp["Group"]["Arn"] == (
        f"arn:aws:quicksight:us-west-2:{ACCOUNT_ID}:group/default/mygroup"
    )
    assert resp["Group"]["GroupName"] == "mygroup"
    assert resp["Group"]["Description"] == "my new fancy group"
    assert resp["Group"]["PrincipalId"] == f"{ACCOUNT_ID}"


@mock_quicksight
def test_update_group():
    client = boto3.client("quicksight", region_name="us-west-2")
    client.create_group(
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
        GroupName="mygroup",
        Description="desc1",
    )

    resp = client.update_group(
        GroupName="mygroup",
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
        Description="desc2",
    )
    assert resp["Group"]["Description"] == "desc2"

    resp = client.describe_group(
        GroupName="mygroup", AwsAccountId=ACCOUNT_ID, Namespace="default"
    )

    assert "Group" in resp
    assert resp["Group"]["Arn"] == (
        f"arn:aws:quicksight:us-west-2:{ACCOUNT_ID}:group/default/mygroup"
    )
    assert resp["Group"]["GroupName"] == "mygroup"
    assert resp["Group"]["Description"] == "desc2"
    assert resp["Group"]["PrincipalId"] == f"{ACCOUNT_ID}"


@mock_quicksight
def test_delete_group():
    client = boto3.client("quicksight", region_name="us-east-2")
    client.create_group(
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
        GroupName="mygroup",
        Description="my new fancy group",
    )

    client.delete_group(
        GroupName="mygroup", AwsAccountId=ACCOUNT_ID, Namespace="default"
    )

    with pytest.raises(ClientError) as exc:
        client.describe_group(
            GroupName="mygroup", AwsAccountId=ACCOUNT_ID, Namespace="default"
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"


@mock_quicksight
def test_list_groups__initial():
    client = boto3.client("quicksight", region_name="us-east-2")
    resp = client.list_groups(AwsAccountId=ACCOUNT_ID, Namespace="default")

    assert resp["GroupList"] == []
    assert resp["Status"] == 200


@mock_quicksight
def test_list_groups():
    client = boto3.client("quicksight", region_name="us-east-1")
    for i in range(4):
        client.create_group(
            AwsAccountId=ACCOUNT_ID, Namespace="default", GroupName=f"group{i}"
        )

    resp = client.list_groups(AwsAccountId=ACCOUNT_ID, Namespace="default")

    assert len(resp["GroupList"]) == 4
    assert resp["Status"] == 200

    assert {
        "Arn": f"arn:aws:quicksight:us-east-1:{ACCOUNT_ID}:group/default/group0",
        "GroupName": "group0",
        "PrincipalId": ACCOUNT_ID,
    } in resp["GroupList"]

    assert {
        "Arn": f"arn:aws:quicksight:us-east-1:{ACCOUNT_ID}:group/default/group3",
        "GroupName": "group3",
        "PrincipalId": ACCOUNT_ID,
    } in resp["GroupList"]
