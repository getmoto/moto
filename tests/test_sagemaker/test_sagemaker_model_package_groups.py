import uuid
from datetime import datetime
from unittest import SkipTest

import boto3
import pytest
from botocore.exceptions import ClientError
from dateutil.tz import tzutc  # type: ignore
from freezegun import freeze_time

from moto import mock_aws, settings

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_aws
def test_create_model_package_group():
    client = boto3.client("sagemaker", region_name="us-east-2")
    resp = client.create_model_package_group(
        ModelPackageGroupName="test-model-package-group",
        ModelPackageGroupDescription="test-model-package-group-description",
        Tags=[
            {"Key": "test-key", "Value": "test-value"},
        ],
    )
    assert (
        resp["ModelPackageGroupArn"]
        == "arn:aws:sagemaker:us-east-2:123456789012:model-package-group/test-model-package-group"
    )


@mock_aws
def test_list_model_package_groups():
    client = boto3.client("sagemaker", region_name="eu-west-1")
    group1 = "test-model-package-group-1"
    desc1 = "test-model-package-group-description-1"
    client.create_model_package_group(
        ModelPackageGroupName=group1, ModelPackageGroupDescription=desc1
    )

    group2 = "test-model-package-group-2"
    desc2 = "test-model-package-group-description-2"
    client.create_model_package_group(
        ModelPackageGroupName=group2,
        ModelPackageGroupDescription=desc2,
    )

    summary = client.list_model_package_groups()["ModelPackageGroupSummaryList"]

    assert summary[0]["ModelPackageGroupName"] == group1
    assert summary[0]["ModelPackageGroupDescription"] == desc1

    assert summary[1]["ModelPackageGroupName"] == group2
    assert summary[1]["ModelPackageGroupDescription"] == desc2

    # Pagination
    resp = client.list_model_package_groups(MaxResults=1)
    assert len(resp["ModelPackageGroupSummaryList"]) == 1

    resp = client.list_model_package_groups(MaxResults=1, NextToken=resp["NextToken"])
    assert len(resp["ModelPackageGroupSummaryList"]) == 1
    assert "NextToken" not in resp


@mock_aws
def test_list_model_package_groups_creation_time_before():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Can't freeze time in ServerMode")
    client = boto3.client("sagemaker", region_name="eu-west-1")
    with freeze_time("2020-01-01 00:00:00"):
        client.create_model_package_group(
            ModelPackageGroupName="test-model-package-group-1",
            ModelPackageGroupDescription="test-model-package-group-description-1",
        )
    with freeze_time("2021-01-01 00:00:00"):
        client.create_model_package_group(
            ModelPackageGroupName="test-model-package-group-2",
            ModelPackageGroupDescription="test-model-package-group-description-2",
        )
    resp = client.list_model_package_groups(CreationTimeBefore="2020-01-01T02:00:00Z")

    assert len(resp["ModelPackageGroupSummaryList"]) == 1


@mock_aws
def test_list_model_package_groups_creation_time_after():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Can't freeze time in ServerMode")
    client = boto3.client("sagemaker", region_name="eu-west-1")
    with freeze_time("2020-01-01 00:00:00"):
        client.create_model_package_group(
            ModelPackageGroupName="test-model-package-group-1",
            ModelPackageGroupDescription="test-model-package-group-description-1",
        )
    with freeze_time("2021-01-01 00:00:00"):
        client.create_model_package_group(
            ModelPackageGroupName="test-model-package-group-2",
            ModelPackageGroupDescription="test-model-package-group-description-2",
        )
    resp = client.list_model_package_groups(CreationTimeAfter="2020-01-02T00:00:00Z")

    assert len(resp["ModelPackageGroupSummaryList"]) == 1


@mock_aws
def test_list_model_package_groups_name_contains():
    client = boto3.client("sagemaker", region_name="eu-west-1")
    client.create_model_package_group(
        ModelPackageGroupName="test-model-package-group-1",
        ModelPackageGroupDescription="test-model-package-group-description-1",
    )
    client.create_model_package_group(
        ModelPackageGroupName="test-model-package-group-2",
        ModelPackageGroupDescription="test-model-package-group-description-2",
    )
    client.create_model_package_group(
        ModelPackageGroupName="another-model-package-group",
        ModelPackageGroupDescription="another-model-package-group-description",
    )
    resp = client.list_model_package_groups(NameContains="test-model-package")

    assert len(resp["ModelPackageGroupSummaryList"]) == 2


@mock_aws
def test_list_model_package_groups_sort_by():
    client = boto3.client("sagemaker", region_name="eu-west-1")
    client.create_model_package_group(
        ModelPackageGroupName="test-model-package-group-1",
        ModelPackageGroupDescription="test-model-package-group-description-1",
    )
    client.create_model_package_group(
        ModelPackageGroupName="test-model-package-group-2",
        ModelPackageGroupDescription="test-model-package-group-description-2",
    )
    resp = client.list_model_package_groups(SortBy="CreationTime")

    assert (
        resp["ModelPackageGroupSummaryList"][0]["ModelPackageGroupName"]
        == "test-model-package-group-1"
    )
    assert (
        resp["ModelPackageGroupSummaryList"][1]["ModelPackageGroupName"]
        == "test-model-package-group-2"
    )


@mock_aws
def test_list_model_package_groups_sort_order():
    client = boto3.client("sagemaker", region_name="eu-west-1")
    client.create_model_package_group(
        ModelPackageGroupName="test-model-package-group-1",
        ModelPackageGroupDescription="test-model-package-group-description-1",
    )
    client.create_model_package_group(
        ModelPackageGroupName="test-model-package-group-2",
        ModelPackageGroupDescription="test-model-package-group-description-2",
    )
    resp = client.list_model_package_groups(SortOrder="Descending")

    assert (
        resp["ModelPackageGroupSummaryList"][0]["ModelPackageGroupName"]
        == "test-model-package-group-2"
    )
    assert (
        resp["ModelPackageGroupSummaryList"][1]["ModelPackageGroupName"]
        == "test-model-package-group-1"
    )


@mock_aws
def test_describe_model_package_group():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Can't freeze time in ServerMode")
    client = boto3.client("sagemaker", region_name="eu-west-1")
    with freeze_time("2020-01-01 00:00:00"):
        client.create_model_package_group(
            ModelPackageGroupName="test-model-package-group",
            ModelPackageGroupDescription="test-model-package-group-description",
        )
    resp = client.describe_model_package_group(
        ModelPackageGroupName="test-model-package-group"
    )
    assert resp["ModelPackageGroupName"] == "test-model-package-group"
    assert (
        resp["ModelPackageGroupDescription"] == "test-model-package-group-description"
    )
    assert (
        resp["ModelPackageGroupArn"]
        == "arn:aws:sagemaker:eu-west-1:123456789012:model-package-group/test-model-package-group"
    )
    assert resp["ModelPackageGroupStatus"] == "Completed"
    assert resp["CreationTime"] == datetime(2020, 1, 1, 0, 0, 0, tzinfo=tzutc())


@mock_aws
def test_describe_model_package_group_not_exists():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Can't freeze time in ServerMode")
    client = boto3.client("sagemaker", region_name="eu-west-1")

    with pytest.raises(ClientError) as e:
        client.describe_model_package_group(
            ModelPackageGroupName="test-model-package-group"
        )

    assert e.value.response["Error"]["Code"] == "ValidationException"
    assert "does not exist" in e.value.response["Error"]["Message"]


@mock_aws
def test_list_tags_model_package_group():
    region_name = "eu-west-1"
    model_package_group_name = "test-model-package-group"
    client = boto3.client("sagemaker", region_name=region_name)
    client.create_model_package_group(
        ModelPackageGroupName=model_package_group_name,
        ModelPackageGroupDescription="test-model-package-group-description",
    )

    tags = []
    for _ in range(80):
        tags.append({"Key": str(uuid.uuid4()), "Value": "myValue"})

    resource_arn = (
        f"arn:aws:sagemaker:{region_name}:123456789012"
        f":model-package-group/{model_package_group_name}"
    )
    _ = client.add_tags(ResourceArn=resource_arn, Tags=tags)

    paginator = client.get_paginator("list_tags")
    response_iterator = paginator.paginate(ResourceArn=resource_arn)
    tags_from_paginator = []
    for response in response_iterator:
        tags_from_paginator.extend(response["Tags"])

    assert tags_from_paginator == tags


@mock_aws
def test_delete_tags_model_package_group():
    region_name = "eu-west-1"
    model_package_group_name = "test-model-package-group"
    client = boto3.client("sagemaker", region_name=region_name)
    client.create_model_package_group(
        ModelPackageGroupName=model_package_group_name,
        ModelPackageGroupDescription="test-model-package-group-description",
    )

    tags = []
    for _ in range(80):
        tags.append({"Key": str(uuid.uuid4()), "Value": "myValue"})

    resource_arn = (
        f"arn:aws:sagemaker:{region_name}:123456789012"
        f":model-package-group/{model_package_group_name}"
    )
    _ = client.add_tags(ResourceArn=resource_arn, Tags=tags)

    delete_tag_keys = [tag["Key"] for tag in tags[:20]]
    _ = client.delete_tags(ResourceArn=resource_arn, TagKeys=delete_tag_keys)

    paginator = client.get_paginator("list_tags")
    response_iterator = paginator.paginate(ResourceArn=resource_arn)
    remaining_tags = []
    for response in response_iterator:
        remaining_tags.extend(response["Tags"])
    assert remaining_tags == tags[20:]
