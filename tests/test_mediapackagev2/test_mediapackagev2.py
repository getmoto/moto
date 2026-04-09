"""Unit tests for mediapackagev2-supported APIs."""

import re
from uuid import uuid4

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from tests import aws_verified

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@aws_verified
@pytest.mark.aws_verified
def test_create_channel_group(account_id):
    client = boto3.client("mediapackagev2", region_name="ap-southeast-1")
    group_name = str(uuid4())

    try:
        group = client.create_channel_group(ChannelGroupName=group_name)

        assert group["ChannelGroupName"] == group_name
        assert (
            group["Arn"]
            == f"arn:aws:mediapackagev2:ap-southeast-1:{account_id}:channelGroup/{group_name}"
        )
        assert re.match(
            pattern=r"[a-z0-9]{6}\.egress\.[a-z0-9]{6}\.mediapackagev2\.ap-southeast-1\.amazonaws\.com",
            string=group["EgressDomain"],
        )
        assert group["CreatedAt"]
        assert group["CreatedAt"] == group["ModifiedAt"]
        assert group["ETag"]
        assert group["Tags"] == {}
    finally:
        client.delete_channel_group(ChannelGroupName=group_name)


@aws_verified
@pytest.mark.aws_verified
def test_get_channel_group(account_id):
    client = boto3.client("mediapackagev2", region_name="us-east-2")

    group_name = str(uuid4())
    try:
        creation = client.create_channel_group(ChannelGroupName=group_name)
        creation.pop("ResponseMetadata")

        group = client.get_channel_group(ChannelGroupName=group_name)
        group.pop("ResponseMetadata")

        # Validation that 'Create' has the right values already happens in another test
        assert creation == group
    finally:
        client.delete_channel_group(ChannelGroupName=group_name)


@mock_aws()
def test_list_channel_groups():
    # This test is explicitly not verified against AWS, for two reasons:
    # - AWS has a soft limit of 3 channel groups (https://docs.aws.amazon.com/mediapackage/latest/userguide/quotas.html)
    # - AWS doesn't return groups immediately. Calling `list_groups` directly after creation will only return a single group.
    #   You may get a second one if you wait 10 seconds - I haven't tested how long one should wait until we get all groups
    client = boto3.client("mediapackagev2", region_name="ap-southeast-1")

    names = [str(uuid4()) for _ in range(5)]
    try:
        for group_name in names:
            client.create_channel_group(ChannelGroupName=group_name)

        all_groups = client.list_channel_groups()["Items"]
        assert [group["ChannelGroupName"] for group in all_groups] == names

        page1 = client.list_channel_groups(MaxResults=3)
        assert [group["ChannelGroupName"] for group in page1["Items"]] == names[:3]

        page2 = client.list_channel_groups(NextToken=page1["NextToken"])
        assert [group["ChannelGroupName"] for group in page2["Items"]] == names[3:]
    finally:
        for group_name in names:
            client.delete_channel_group(ChannelGroupName=group_name)


@aws_verified
@pytest.mark.aws_verified
def test_get_channel_group_unknown():
    client = boto3.client("mediapackagev2", region_name="us-east-2")

    group_name = str(uuid4())
    with pytest.raises(ClientError) as exc:
        client.get_channel_group(ChannelGroupName=group_name)
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert (
        err["Message"]
        == "MediaPackage can't process your request because we can't find your channel group. Verify your channel group name or add a channel group and then try again"
    )


@aws_verified
@pytest.mark.aws_verified
def test_delete_channel_group():
    client = boto3.client("mediapackagev2", region_name="us-east-2")

    group_name = str(uuid4())
    client.create_channel_group(ChannelGroupName=group_name)

    client.delete_channel_group(ChannelGroupName=group_name)

    # Verify group is deleted
    with pytest.raises(ClientError) as exc:
        client.get_channel_group(ChannelGroupName=group_name)
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"

    # Operation is idempotent
    client.delete_channel_group(ChannelGroupName=group_name)

    # Deleting unknown channels is also fine
    client.delete_channel_group(ChannelGroupName=str(uuid4()))


@aws_verified
@pytest.mark.aws_verified
def test_delete_channel_group_thats_not_empty():
    client = boto3.client("mediapackagev2", region_name="us-east-2")

    group_name = str(uuid4())
    channel_name = str(uuid4())
    client.create_channel_group(ChannelGroupName=group_name)

    # Create channels
    client.create_channel(ChannelGroupName=group_name, ChannelName=channel_name)

    # Initial deletion will fail
    with pytest.raises(ClientError) as exc:
        client.delete_channel_group(ChannelGroupName=group_name)
    err = exc.value.response["Error"]
    assert err["Code"] == "ConflictException"
    assert (
        err["Message"]
        == "The channel group you tried to delete has channels attached to it. If you want to delete this channel group, you must first delete the channels attached to it"
    )

    # Delete Channels
    client.delete_channel(ChannelGroupName=group_name, ChannelName=channel_name)

    # Retry deletion
    client.delete_channel_group(ChannelGroupName=group_name)

    # Verify group is deleted
    with pytest.raises(ClientError) as exc:
        client.get_channel_group(ChannelGroupName=group_name)
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"


@aws_verified
@pytest.mark.aws_verified
def test_create_channel(account_id):
    client = boto3.client("mediapackagev2", region_name="eu-west-1")
    group_name = str(uuid4())
    channel_name = str(uuid4())
    try:
        group = client.create_channel_group(ChannelGroupName=group_name)
        domain = group["EgressDomain"]

        channel = client.create_channel(
            ChannelGroupName=group_name, ChannelName=channel_name
        )

        assert (
            channel["Arn"]
            == f"arn:aws:mediapackagev2:eu-west-1:{account_id}:channelGroup/{group_name}/channel/{channel_name}"
        )
        assert channel["ChannelName"] == channel_name
        assert channel["ChannelGroupName"] == group_name

        # xxxxxx.egress.yyyyyy.mediapackagev2.eu-west-1.amazonaws.com --> xxxxxx-1.ingest.yyyyyy.mediapackagev2.eu-west-1.amazonaws.com
        domain1 = domain.replace(".egress", "-1.ingest")
        domain2 = domain.replace(".egress", "-2.ingest")
        assert channel["IngestEndpoints"] == [
            {
                "Id": "1",
                "Url": f"https://{domain1}/in/v1/{group_name}/1/{channel_name}/index",
            },
            {
                "Id": "2",
                "Url": f"https://{domain2}/in/v1/{group_name}/2/{channel_name}/index",
            },
        ]

        assert channel["ETag"]
        assert channel["Tags"] == {}

        assert channel["InputSwitchConfiguration"] == {"MQCSInputSwitching": False}
        assert channel["OutputHeaderConfiguration"] == {"PublishMQCS": False}

    finally:
        client.delete_channel(ChannelGroupName=group_name, ChannelName=channel_name)
        client.delete_channel_group(ChannelGroupName=group_name)


@aws_verified
@pytest.mark.aws_verified
def test_get_channel():
    client = boto3.client("mediapackagev2", region_name="us-east-1")
    group_name = str(uuid4())
    channel_name = str(uuid4())
    try:
        client.create_channel_group(ChannelGroupName=group_name)

        creation = client.create_channel(
            ChannelGroupName=group_name, ChannelName=channel_name
        )
        creation.pop("ResponseMetadata")

        channel = client.get_channel(
            ChannelGroupName=group_name, ChannelName=channel_name
        )
        channel.pop("ResponseMetadata")

        # We already know that 'create_channel' returns the correct values
        # 'get_channel' just has a single additional field that we need to verify
        assert channel.pop("InputType") == "HLS"
        assert creation == channel

    finally:
        client.delete_channel(ChannelGroupName=group_name, ChannelName=channel_name)
        client.delete_channel_group(ChannelGroupName=group_name)


@aws_verified
@pytest.mark.aws_verified
def test_get_channel_unknown():
    client = boto3.client("mediapackagev2", region_name="us-east-2")

    group_name = str(uuid4())
    channel_name = str(uuid4())

    # Get Channel in Unknown Group
    with pytest.raises(ClientError) as exc:
        client.get_channel(ChannelGroupName=group_name, ChannelName=channel_name)
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert (
        err["Message"]
        == "MediaPackage can't process your request because we can't find your channel group. Verify your channel group name or add a channel group and then try again"
    )

    try:
        client.create_channel_group(ChannelGroupName=group_name)

        # Get Unknown Channel in Existing Group
        with pytest.raises(ClientError) as exc:
            client.get_channel(ChannelGroupName=group_name, ChannelName=channel_name)
        err = exc.value.response["Error"]
        assert err["Code"] == "ResourceNotFoundException"
        assert (
            err["Message"]
            == "MediaPackage can't process your request because we can't find your channel. Verify your channel name or add a channel and then try again"
        )

    finally:
        client.delete_channel_group(ChannelGroupName=group_name)


@aws_verified
@pytest.mark.aws_verified
def test_delete_channel():
    client = boto3.client("mediapackagev2", region_name="us-east-2")

    group_name = str(uuid4())
    channel_name = str(uuid4())
    try:
        client.create_channel_group(ChannelGroupName=group_name)

        client.create_channel(ChannelGroupName=group_name, ChannelName=channel_name)

        client.delete_channel(ChannelGroupName=group_name, ChannelName=channel_name)

        # Verify group is deleted
        with pytest.raises(ClientError) as exc:
            client.get_channel(ChannelGroupName=group_name, ChannelName=channel_name)
        assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"

        # Operation is idempotent
        client.delete_channel(ChannelGroupName=group_name, ChannelName=channel_name)

        # Deleting unknown channels is also fine
        client.delete_channel(ChannelGroupName=group_name, ChannelName=str(uuid4()))

    finally:
        client.delete_channel_group(ChannelGroupName=group_name)
