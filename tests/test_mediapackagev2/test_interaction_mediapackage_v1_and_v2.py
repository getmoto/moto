from uuid import uuid4

import boto3
import pytest
from botocore.exceptions import ClientError

from tests import aws_verified

"""
Some services will have two API's that act on the same resources, like SES and SESv2.

These tests are here simply to verify that, for MediaPackage, there is no overlap.

V1 Channels cannot be retrieved in V2, nor vice versa 
"""


@aws_verified
@pytest.mark.aws_verified
def test_v1_create__v2_retrieve(account_id):
    clientv1 = boto3.client("mediapackage", region_name="ap-southeast-1")
    clientv2 = boto3.client("mediapackagev2", region_name="ap-southeast-1")
    channel_name = str(uuid4())

    try:
        clientv1.create_channel(Id=channel_name)

        assert clientv2.list_channel_groups()["Items"] == []

        # Listing Channels requires a ChannelGroup
        # But this is not known, so we cannot use this API
    finally:
        clientv1.delete_channel(Id=channel_name)


@aws_verified
@pytest.mark.aws_verified
def test_v2_create__v1_retrieve(account_id):
    clientv1 = boto3.client("mediapackage", region_name="ap-southeast-1")
    clientv2 = boto3.client("mediapackagev2", region_name="ap-southeast-1")
    group_name = str(uuid4())
    channel_name = str(uuid4())

    try:
        clientv2.create_channel_group(ChannelGroupName=group_name)
        channel = clientv2.create_channel(
            ChannelGroupName=group_name, ChannelName=channel_name
        )

        assert clientv1.list_channels()["Channels"] == []

        with pytest.raises(ClientError):
            clientv1.describe_channel(Id=channel["Arn"])

        with pytest.raises(ClientError):
            clientv1.describe_channel(Id=channel_name)

    finally:
        clientv2.delete_channel(ChannelGroupName=group_name, ChannelName=channel_name)
        clientv2.delete_channel_group(ChannelGroupName=group_name)
