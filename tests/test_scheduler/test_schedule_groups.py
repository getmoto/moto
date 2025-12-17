import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_aws
def test_create_get_delete_schedule_group():
    client = boto3.client("scheduler", region_name="eu-west-1")
    arn = client.create_schedule_group(Name="sg")["ScheduleGroupArn"]

    assert arn == f"arn:aws:scheduler:eu-west-1:{DEFAULT_ACCOUNT_ID}:schedule-group/sg"

    group = client.get_schedule_group(Name="sg")
    assert group["Arn"] == arn
    assert group["Name"] == "sg"
    assert group["State"] == "ACTIVE"

    client.delete_schedule_group(Name="sg")

    with pytest.raises(ClientError) as exc:
        client.get_schedule_group(Name="sg")
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"


@mock_aws
def test_list_schedule_groups():
    client = boto3.client("scheduler", region_name="ap-southeast-1")

    # The default group is always active
    groups = client.list_schedule_groups()["ScheduleGroups"]
    assert len(groups) == 1
    assert (
        groups[0]["Arn"]
        == f"arn:aws:scheduler:ap-southeast-1:{DEFAULT_ACCOUNT_ID}:schedule-group/default"
    )

    arn1 = client.create_schedule_group(Name="sg")["ScheduleGroupArn"]

    groups = client.list_schedule_groups()["ScheduleGroups"]
    assert len(groups) == 2
    assert groups[1]["Arn"] == arn1


@mock_aws
def test_get_schedule_groupe_not_found():
    client = boto3.client("scheduler", region_name="eu-west-1")

    with pytest.raises(ClientError) as exc:
        client.get_schedule_group(Name="sg")
    err = exc.value.response["Error"]
    assert err["Message"] == "Schedule group sg does not exist."
    assert err["Code"] == "ResourceNotFoundException"
    assert exc.value.response["ResponseMetadata"]["HTTPStatusCode"] == 404


@mock_aws
def test_list_schedule_groups_with_filters():
    client = boto3.client("scheduler", region_name="ap-southeast-1")

    # Create test schedule groups
    groups_to_create = ["blabla-1", "blabla-2", "other-1", "blabla-3", "other-2"]

    for group in groups_to_create:
        client.create_schedule_group(Name=group)

    # Test NamePrefix filter
    groups = client.list_schedule_groups(NamePrefix="blabla")["ScheduleGroups"]
    # +1 for default group
    assert len(groups) == 3
    group_names = [g["Name"] for g in groups if g["Name"] != "default"]
    assert all(name.startswith("blabla") for name in group_names)
    assert "other-1" not in group_names
    assert "other-2" not in group_names

    # Test MaxResults filter
    groups = client.list_schedule_groups(MaxResults=2)["ScheduleGroups"]
    assert len(groups) == 2
    assert "NextToken" in client.list_schedule_groups(MaxResults=2)

    # Test both filters together
    groups = client.list_schedule_groups(NamePrefix="blabla", MaxResults=2)[
        "ScheduleGroups"
    ]
    assert len(groups) == 2
    filtered_groups = [g for g in groups if g["Name"] != "default"]
    assert all(g["Name"].startswith("blabla") for g in filtered_groups)
    assert "NextToken" in client.list_schedule_groups(NamePrefix="blabla", MaxResults=2)
