from __future__ import unicode_literals

import boto3
import sure  # noqa
from moto import mock_mediapackage
region = "eu-west-1"


def _create_channel_config(**kwargs):
    id = kwargs.get("id", "channel-id")
    description = kwargs.get("description", "Awesome channel!")
    tags = kwargs.get("tags", {"Customer": "moto"})
    channel_config = dict(
        Description=description,
        Id=id,
        Tags=tags,
    )
    return channel_config

@mock_mediapackage
def test_create_channel_succeeds():
    client = boto3.client("mediapackage", region_name=region)
    channel_config = _create_channel_config()

    response = client.create_channel(**channel_config)
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    response["Arn"].should.equal(
        "arn:aws:mediapackage:channel:{}".format(response["Id"])
    )
    response["Description"].should.equal("Awesome channel!")
    response["Id"].should.equal("channel-id")
    response["Tags"]["Customer"].should.equal("moto")

@mock_mediapackage
def test_describe_channel_succeeds():
    client = boto3.client("mediapackage", region_name=region)
    channel_config = _create_channel_config()

    create_response = client.create_channel(**channel_config)
    describe_response = client.describe_channel(
        Id=create_response["Id"]
    )
    describe_response["Arn"].should.equal(
        "arn:aws:mediapackage:channel:{}".format(describe_response["Id"])
    )
    describe_response["Description"].should.equal(channel_config["Description"])
    describe_response["Tags"]["Customer"].should.equal("moto")


@mock_mediapackage
def test_delete_channel_moves_channel_in_deleted_state():
    client = boto3.client("mediapackage", region_name=region)
    channel_config = _create_channel_config()
    create_response = client.create_channel(**channel_config)
    # Before deletion
    list_response = client.list_channels()
    channels_list = list_response["Channels"]
    delete_response = client.delete_channel(Id=create_response["Id"])
    # After deletion
    post_deletion_list_response = client.list_channels()
    post_deletion_channels_list = post_deletion_list_response["Channels"]
    len(post_deletion_channels_list).should.equal(len(channels_list) - 1)
    
