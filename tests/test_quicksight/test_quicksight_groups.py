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


@mock_aws
def test_list_groups__paginated():
    client = boto3.client("quicksight", region_name="us-east-1")
    for i in range(125):
        client.create_group(
            AwsAccountId=ACCOUNT_ID, Namespace="default", GroupName=f"group{i}"
        )
    # default pagesize is 100
    page1 = client.list_groups(AwsAccountId=ACCOUNT_ID, Namespace="default")
    assert len(page1["GroupList"]) == 100
    assert "NextToken" in page1

    # We can ask for a smaller pagesize
    page2 = client.list_groups(
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
        MaxResults=15,
        NextToken=page1["NextToken"],
    )
    assert len(page2["GroupList"]) == 15
    assert "NextToken" in page2

    # We could request all of them in one go
    all_users = client.list_groups(
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
        MaxResults=1000,
    )
    length = len(all_users["GroupList"])
    # We don't know exactly how much workspaces there are, because we are running multiple tests at the same time
    assert length >= 125


@mock_aws
def test_search_groups():
    client = boto3.client("quicksight", region_name="us-east-1")
    for i in range(4):
        group_name = f"group{i}" if i < 2 else f"test{i}@test"
        client.create_group(
            AwsAccountId=ACCOUNT_ID, Namespace="default", GroupName=group_name
        )

    resp = client.search_groups(
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
        Filters=[
            {"Operator": "StringEquals", "Name": "GROUP_NAME", "Value": "group1"},
        ],
    )

    assert len(resp["GroupList"]) == 1
    assert resp["Status"] == 200

    assert {
        "Arn": f"arn:aws:quicksight:us-east-1:{ACCOUNT_ID}:group/default/group1",
        "GroupName": "group1",
        "PrincipalId": ACCOUNT_ID,
    } in resp["GroupList"]


@mock_aws
def test_search_groups__paginated():
    client = boto3.client("quicksight", region_name="us-east-1")
    for i in range(250):
        group_name = f"group{i}" if i % 2 else f"test{i}@test"
        client.create_group(
            AwsAccountId=ACCOUNT_ID, Namespace="default", GroupName=group_name
        )

    # default pagesize is 100
    page1 = client.search_groups(
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
        Filters=[
            {"Operator": "StartsWith", "Name": "GROUP_NAME", "Value": "group"},
        ],
    )
    assert len(page1["GroupList"]) == 100
    assert "NextToken" in page1

    # We can ask for a smaller pagesize
    page2 = client.search_groups(
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
        Filters=[
            {"Operator": "StartsWith", "Name": "GROUP_NAME", "Value": "group"},
        ],
        MaxResults=15,
        NextToken=page1["NextToken"],
    )
    assert len(page2["GroupList"]) == 15
    assert "NextToken" in page2

    # We could request all of them in one go
    all_users = client.search_groups(
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
        Filters=[
            {"Operator": "StartsWith", "Name": "GROUP_NAME", "Value": "group"},
        ],
        MaxResults=1000,
    )
    length = len(all_users["GroupList"])
    # We don't know exactly how much workspaces there are, because we are running multiple tests at the same time
    assert length >= 125


@mock_aws
def test_list_groups__diff_account_region():
    ACCOUNT_ID_2 = "998877665544"
    client_us = boto3.client("quicksight", region_name="us-east-2")
    client_eu = boto3.client("quicksight", region_name="eu-west-1")
    resp = client_us.create_group(
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
        GroupName="group_us_1",
        Description="Group in US Account 1",
    )
    resp = client_us.create_group(
        AwsAccountId=ACCOUNT_ID_2,
        Namespace="default",
        GroupName="group_us_2",
        Description="Group in US Account 2",
    )
    resp = client_eu.create_group(
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
        GroupName="group_eu_1",
        Description="Group in EU Account 1",
    )

    # Return Account 1, Region US
    resp = client_us.list_groups(AwsAccountId=ACCOUNT_ID, Namespace="default")
    assert len(resp["GroupList"]) == 1
    assert resp["Status"] == 200

    resp["GroupList"][0].pop("PrincipalId")

    assert resp["GroupList"][0] == {
        "Arn": f"arn:aws:quicksight:us-east-2:{ACCOUNT_ID}:group/default/group_us_1",
        "GroupName": "group_us_1",
        "Description": "Group in US Account 1",
    }

    # Return Account 2, Region US
    resp = client_us.list_groups(AwsAccountId=ACCOUNT_ID_2, Namespace="default")

    assert len(resp["GroupList"]) == 1
    assert resp["Status"] == 200

    resp["GroupList"][0].pop("PrincipalId")

    assert resp["GroupList"][0] == {
        "Arn": f"arn:aws:quicksight:us-east-2:{ACCOUNT_ID_2}:group/default/group_us_2",
        "GroupName": "group_us_2",
        "Description": "Group in US Account 2",
    }

    # Return Account 1, Region EU
    resp = client_eu.list_groups(AwsAccountId=ACCOUNT_ID, Namespace="default")

    assert len(resp["GroupList"]) == 1
    assert resp["Status"] == 200

    resp["GroupList"][0].pop("PrincipalId")

    assert resp["GroupList"][0] == {
        "Arn": f"arn:aws:quicksight:eu-west-1:{ACCOUNT_ID}:group/default/group_eu_1",
        "GroupName": "group_eu_1",
        "Description": "Group in EU Account 1",
    }


@mock_aws
def test_search_groups__check_exceptions():
    client = boto3.client("quicksight", region_name="us-east-1")
    # Just do an exception test. No need to create a group first.

    with pytest.raises(ClientError) as exc:
        client.search_groups(
            AwsAccountId=ACCOUNT_ID,
            Namespace="default",
            Filters=[
                {
                    "Operator": "StringEquals",
                    "Name": "GROUP_DESCRIPTION",
                    "Value": "My Group 1",
                },
            ],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
