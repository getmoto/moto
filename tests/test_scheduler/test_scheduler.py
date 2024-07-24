from datetime import datetime

import boto3
import pytest
from botocore.client import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_aws
def test_create_get_schedule():
    client = boto3.client("scheduler", region_name="eu-west-1")
    arn = client.create_schedule(
        Name="my-schedule",
        ScheduleExpression="some cron",
        FlexibleTimeWindow={
            "MaximumWindowInMinutes": 4,
            "Mode": "OFF",
        },
        Target={
            "Arn": "not supported yet",
            "RoleArn": "n/a",
        },
        ActionAfterCompletion="DELETE",
    )["ScheduleArn"]

    assert (
        arn
        == f"arn:aws:scheduler:eu-west-1:{DEFAULT_ACCOUNT_ID}:schedule/default/my-schedule"
    )

    resp = client.get_schedule(Name="my-schedule")
    assert resp["Arn"] == arn
    assert resp["Name"] == "my-schedule"
    assert resp["ScheduleExpression"] == "some cron"
    assert resp["FlexibleTimeWindow"] == {
        "MaximumWindowInMinutes": 4,
        "Mode": "OFF",
    }
    assert resp["ActionAfterCompletion"] == "DELETE"
    assert resp["Target"] == {
        "Arn": "not supported yet",
        "RoleArn": "n/a",
        "RetryPolicy": {"MaximumEventAgeInSeconds": 86400, "MaximumRetryAttempts": 185},
    }
    assert isinstance(resp["CreationDate"], datetime)
    assert isinstance(resp["LastModificationDate"], datetime)
    assert resp["CreationDate"] == resp["LastModificationDate"]


@mock_aws
def test_create_get_delete__in_different_group():
    client = boto3.client("scheduler", region_name="eu-west-1")

    client.create_schedule_group(Name="sg")
    schedule_arn = client.create_schedule(
        Name="my-schedule",
        GroupName="sg",
        ScheduleExpression="some cron",
        FlexibleTimeWindow={
            "MaximumWindowInMinutes": 4,
            "Mode": "OFF",
        },
        Target={
            "Arn": "not supported yet",
            "RoleArn": "n/a",
        },
    )["ScheduleArn"]

    assert (
        schedule_arn
        == "arn:aws:scheduler:eu-west-1:123456789012:schedule/sg/my-schedule"
    )

    schedule = client.get_schedule(GroupName="sg", Name="my-schedule")
    assert schedule["Arn"] == schedule_arn

    client.delete_schedule(GroupName="sg", Name="my-schedule")

    with pytest.raises(ClientError) as exc:
        client.get_schedule(GroupName="sg", Name="my-schedule")
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"


@pytest.mark.parametrize(
    "extra_kwargs",
    [
        ({}),
        ({"GroupName": "some-group"}),
    ],
    ids=["without_group", "with_group"],
)
@mock_aws
def test_update_schedule(extra_kwargs):
    client = boto3.client("scheduler", region_name="eu-west-1")

    client.create_schedule_group(Name="some-group")

    client.create_schedule(
        **extra_kwargs,
        Name="my-schedule",
        ScheduleExpression="some cron",
        FlexibleTimeWindow={
            "MaximumWindowInMinutes": 4,
            "Mode": "OFF",
        },
        Target={
            "Arn": "not supported yet",
            "RoleArn": "n/a",
        },
    )

    client.update_schedule(
        **extra_kwargs,
        Name="my-schedule",
        Description="new desc",
        ScheduleExpression="new cron",
        FlexibleTimeWindow={
            "MaximumWindowInMinutes": 4,
            "Mode": "OFF",
        },
        State="DISABLED",
        Target={
            "Arn": "different arn",
            "RoleArn": "n/a",
        },
    )

    schedule = client.get_schedule(**extra_kwargs, Name="my-schedule")
    assert schedule["Description"] == "new desc"
    assert schedule["ScheduleExpression"] == "new cron"
    assert schedule["State"] == "DISABLED"
    assert schedule["Target"] == {
        "Arn": "different arn",
        "RoleArn": "n/a",
        "RetryPolicy": {"MaximumEventAgeInSeconds": 86400, "MaximumRetryAttempts": 185},
    }

    assert isinstance(schedule["CreationDate"], datetime)
    assert isinstance(schedule["LastModificationDate"], datetime)
    assert schedule["CreationDate"] != schedule["LastModificationDate"]


@mock_aws
def test_create_duplicate_schedule():
    client = boto3.client("scheduler", region_name="us-east-1")
    params = {
        "ScheduleExpression": "at(2022-12-12T00:00:00)",
        "FlexibleTimeWindow": {
            "MaximumWindowInMinutes": 4,
            "Mode": "FLEXIBLE",
        },
        "Target": {"Arn": "arn1", "RoleArn": "arn2"},
    }

    client.create_schedule(Name="schedule1", **params)
    with pytest.raises(ClientError) as exc:
        client.create_schedule(Name="schedule1", **params)
    err = exc.value.response["Error"]
    assert err["Code"] == "ConflictException"
    assert err["Message"] == "Schedule schedule1 already exists."


@mock_aws
def test_get_schedule_for_unknown_group():
    client = boto3.client("scheduler", region_name="eu-west-1")

    with pytest.raises(ClientError) as exc:
        client.get_schedule(GroupName="unknown", Name="my-schedule")
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"


@mock_aws
def test_get_schedule_for_none_existing_schedule():
    client = boto3.client("scheduler", region_name="eu-west-1")

    with pytest.raises(ClientError) as exc:
        client.get_schedule(Name="my-schedule")
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "Schedule my-schedule does not exist."


@mock_aws
def test_list_schedules():
    client = boto3.client("scheduler", region_name="eu-west-1")

    schedules = client.list_schedules()["Schedules"]
    assert schedules == []

    client.create_schedule_group(Name="group2")

    for group in ["default", "group2"]:
        for schedule in ["sch1", "sch2"]:
            for state in ["ENABLED", "DISABLED"]:
                client.create_schedule(
                    Name=f"{schedule}_{state}",
                    GroupName=group,
                    State=state,
                    ScheduleExpression="some cron",
                    FlexibleTimeWindow={"MaximumWindowInMinutes": 4, "Mode": "OFF"},
                    Target={"Arn": "not supported yet", "RoleArn": "n/a"},
                )

    schedules = client.list_schedules()["Schedules"]
    assert len(schedules) == 8
    # The ListSchedules command should not return the entire Target-dictionary
    assert schedules[0]["Target"] == {"Arn": "not supported yet"}

    schedules = client.list_schedules(GroupName="group2")["Schedules"]
    assert len(schedules) == 4

    schedules = client.list_schedules(State="ENABLED")["Schedules"]
    assert len(schedules) == 4


@mock_aws
def test_delete_schedule_for_none_existing_schedule():
    client = boto3.client("scheduler", region_name="eu-west-1")

    with pytest.raises(ClientError) as exc:
        client.delete_schedule(Name="my-schedule")
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "Schedule my-schedule does not exist."
