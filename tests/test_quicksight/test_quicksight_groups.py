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
            "GroupName": "mygroup",
            "Description": "my new fancy group",
        },
        {
            "GroupName": "users@munich",
            "Description": "all munich users",
        },
    ],
)
@mock_aws
def test_create_group(request_params):
    client = boto3.client("quicksight", region_name="us-west-2")
    resp = client.create_group(
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
        GroupName=request_params["GroupName"],
        Description=request_params["Description"],
    )

    assert "Group" in resp

    assert resp["Group"]["Arn"] == (
        f"arn:aws:quicksight:us-west-2:{ACCOUNT_ID}:group/default/{request_params['GroupName']}"
    )
    assert resp["Group"]["GroupName"] == request_params["GroupName"]
    assert resp["Group"]["Description"] == request_params["Description"]
    assert resp["Group"]["PrincipalId"] == f"{ACCOUNT_ID}"


@pytest.mark.parametrize(
    "request_params",
    [
        {
            "GroupName": "mygroup",
            "Description": "my new fancy group",
        },
        {
            "GroupName": "users@munich",
            "Description": "all munich users",
        },
    ],
)
@mock_aws
def test_describe_group(request_params):
    client = boto3.client("quicksight", region_name="us-west-2")
    client.create_group(
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
        GroupName=request_params["GroupName"],
        Description=request_params["Description"],
    )

    resp = client.describe_group(
        GroupName=request_params["GroupName"],
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
    )

    assert "Group" in resp

    assert resp["Group"]["Arn"] == (
        f"arn:aws:quicksight:us-west-2:{ACCOUNT_ID}:group/default/{request_params['GroupName']}"
    )
    assert resp["Group"]["GroupName"] == request_params["GroupName"]
    assert resp["Group"]["Description"] == request_params["Description"]
    assert resp["Group"]["PrincipalId"] == f"{ACCOUNT_ID}"


@pytest.mark.parametrize(
    "request_params",
    [
        {
            "GroupName": "mygroup",
            "Description": "my new fancy group",
        },
        {
            "GroupName": "users@munich",
            "Description": "all munich users",
        },
    ],
)
@mock_aws
def test_update_group(request_params):
    client = boto3.client("quicksight", region_name="us-west-2")
    client.create_group(
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
        GroupName=request_params["GroupName"],
        Description="desc1",
    )

    resp = client.update_group(
        GroupName=request_params["GroupName"],
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
        Description="desc2",
    )
    assert resp["Group"]["Description"] == "desc2"

    resp = client.describe_group(
        GroupName=request_params["GroupName"],
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
    )

    assert "Group" in resp
    assert resp["Group"]["Arn"] == (
        f"arn:aws:quicksight:us-west-2:{ACCOUNT_ID}:group/default/{request_params['GroupName']}"
    )
    assert resp["Group"]["GroupName"] == request_params["GroupName"]
    assert resp["Group"]["Description"] == "desc2"
    assert resp["Group"]["PrincipalId"] == f"{ACCOUNT_ID}"


@pytest.mark.parametrize(
    "request_params",
    [
        {
            "GroupName": "mygroup",
            "Description": "my new fancy group",
        },
        {
            "GroupName": "users@munich",
            "Description": "all munich users",
        },
    ],
)
@mock_aws
def test_delete_group(request_params):
    client = boto3.client("quicksight", region_name="us-east-2")
    client.create_group(
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
        GroupName=request_params["GroupName"],
        Description=request_params["Description"],
    )

    client.delete_group(
        GroupName=request_params["GroupName"],
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
    )

    with pytest.raises(ClientError) as exc:
        client.describe_group(
            GroupName=request_params["GroupName"],
            AwsAccountId=ACCOUNT_ID,
            Namespace="default",
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"


@mock_aws
def test_list_groups__initial():
    client = boto3.client("quicksight", region_name="us-east-2")
    resp = client.list_groups(AwsAccountId=ACCOUNT_ID, Namespace="default")

    assert resp["GroupList"] == []
    assert resp["Status"] == 200


@mock_aws
def test_list_groups():
    client = boto3.client("quicksight", region_name="us-east-1")
    for i in range(4):
        group_name = f"group{i}" if i < 2 else f"group{i}@test"
        client.create_group(
            AwsAccountId=ACCOUNT_ID, Namespace="default", GroupName=group_name
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
        "Arn": f"arn:aws:quicksight:us-east-1:{ACCOUNT_ID}:group/default/group3@test",
        "GroupName": "group3@test",
        "PrincipalId": ACCOUNT_ID,
    } in resp["GroupList"]
