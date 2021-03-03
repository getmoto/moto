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
def test_list():
    # do test
    pass


@mock_mediapackage
def test_create_channel_succeeds():
    client = boto3.client("mediapackage", region_name=region)
    channel_config = _create_channel_config()

    response = client.create_channel(**channel_config)

    print("RESPONSE ==>:", response)
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    response["Channel"]["Arn"].should.equal(
        "arn:aws:mediapackage:channel:{}".format(response["Channel"]["Id"])
    )
    response["Channel"]["Description"].should.equal("Awesome channel!")
    response["Channel"]["Id"].should.equal("channel-id")
    response["Channel"]["Tags"]["Customer"].should.equal("moto")
