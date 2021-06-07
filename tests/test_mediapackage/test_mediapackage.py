from __future__ import unicode_literals

import boto3
import pytest
import sure  # noqa
from botocore.exceptions import ClientError  # Boto3 will always throw this exception

from moto import mock_mediapackage

region = "eu-west-1"


def _create_channel_config(**kwargs):
    id = kwargs.get("id", "channel-id")
    description = kwargs.get("description", "Awesome channel!")
    tags = kwargs.get("tags", {"Customer": "moto"})
    channel_config = dict(Description=description, Id=id, Tags=tags)
    return channel_config


def _create_origin_endpoint_config(**kwargs):
    authorization = kwargs.get(
        "authorization",
        {"CdnIdentifierSecret": "cdn-id-secret", "SecretsRoleArn": "secrets-arn"},
    )
    channel_id = kwargs.get("channel_id", "channel-id")
    cmaf_package = kwargs.get("cmafpackage", {"HlsManifests": []})
    dash_package = kwargs.get("dash_package", {"AdTriggers": []})
    description = kwargs.get("description", "channel-description")
    hls_package = kwargs.get("hls_package", {"AdMarkers": "NONE"})
    id = kwargs.get("id", "origin-endpoint-id")
    manifest_name = kwargs.get("manifest_name", "manifest-name")
    mss_package = kwargs.get("mss_package", {"ManifestWindowSeconds": 1})
    origination = kwargs.get("origination", "ALLOW")
    startover_window_seconds = kwargs.get("startover_window_seconds", 1)
    tags = kwargs.get("tags", {"Customer": "moto"})
    time_delay_seconds = kwargs.get("time_delay_seconds", 1)
    whitelist = kwargs.get("whitelist", ["whitelist"])
    origin_endpoint_config = dict(
        Authorization=authorization,
        ChannelId=channel_id,
        CmafPackage=cmaf_package,
        DashPackage=dash_package,
        Description=description,
        HlsPackage=hls_package,
        Id=id,
        ManifestName=manifest_name,
        MssPackage=mss_package,
        Origination=origination,
        StartoverWindowSeconds=startover_window_seconds,
        Tags=tags,
        TimeDelaySeconds=time_delay_seconds,
        Whitelist=whitelist,
    )
    return origin_endpoint_config


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
    describe_response = client.describe_channel(Id=create_response["Id"])
    describe_response["Arn"].should.equal(
        "arn:aws:mediapackage:channel:{}".format(describe_response["Id"])
    )
    describe_response["Description"].should.equal(channel_config["Description"])
    describe_response["Tags"]["Customer"].should.equal("moto")


@mock_mediapackage
def test_describe_unknown_channel_throws_error():
    client = boto3.client("mediapackage", region_name=region)
    channel_id = "unknown-channel"
    with pytest.raises(ClientError) as err:
        client.describe_channel(Id=channel_id)
    err = err.value.response["Error"]
    err["Code"].should.equal("NotFoundException")
    err["Message"].should.equal("channel with id={} not found".format(str(channel_id)))


@mock_mediapackage
def test_delete_channel_successfully_deletes():
    client = boto3.client("mediapackage", region_name=region)
    channel_config = _create_channel_config()
    create_response = client.create_channel(**channel_config)
    # Before deletion
    list_response = client.list_channels()
    channels_list = list_response["Channels"]
    client.delete_channel(Id=create_response["Id"])
    # After deletion
    post_deletion_list_response = client.list_channels()
    post_deletion_channels_list = post_deletion_list_response["Channels"]
    len(post_deletion_channels_list).should.equal(len(channels_list) - 1)


@mock_mediapackage
def test_list_channels_succeds():
    channels_list = []
    client = boto3.client("mediapackage", region_name=region)
    channel_config = _create_channel_config()
    len(channels_list).should.equal(0)
    client.create_channel(**channel_config)
    list_response = client.list_channels()
    channels_list = list_response["Channels"]
    len(channels_list).should.equal(1)
    first_channel = channels_list[0]
    first_channel["Arn"].should.equal(
        "arn:aws:mediapackage:channel:{}".format(first_channel["Id"])
    )
    first_channel["Description"].should.equal(channel_config["Description"])
    first_channel["Tags"]["Customer"].should.equal("moto")


@mock_mediapackage
def test_create_origin_endpoint_succeeds():
    client = boto3.client("mediapackage", region_name=region)
    origin_endpoint_config = _create_origin_endpoint_config()

    response = client.create_origin_endpoint(**origin_endpoint_config)
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    response["Arn"].should.equal(
        "arn:aws:mediapackage:origin_endpoint:{}".format(response["Id"])
    )
    response["ChannelId"].should.equal(origin_endpoint_config["ChannelId"])
    response["Description"].should.equal(origin_endpoint_config["Description"])
    response["HlsPackage"].should.equal(origin_endpoint_config["HlsPackage"])
    response["Origination"].should.equal("ALLOW")


@mock_mediapackage
def test_describe_origin_endpoint_succeeds():
    client = boto3.client("mediapackage", region_name=region)
    origin_endpoint_config = _create_origin_endpoint_config()

    create_response = client.create_origin_endpoint(**origin_endpoint_config)
    describe_response = client.describe_origin_endpoint(Id=create_response["Id"])
    describe_response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    describe_response["Arn"].should.equal(
        "arn:aws:mediapackage:origin_endpoint:{}".format(describe_response["Id"])
    )
    describe_response["ChannelId"].should.equal(origin_endpoint_config["ChannelId"])
    describe_response["Description"].should.equal(origin_endpoint_config["Description"])
    describe_response["HlsPackage"].should.equal(origin_endpoint_config["HlsPackage"])
    describe_response["Origination"].should.equal("ALLOW")
    describe_response["Url"].should.equal(
        "https://origin-endpoint.mediapackage.{}.amazonaws.com/{}".format(
            region, describe_response["Id"]
        )
    )


@mock_mediapackage
def test_delete_origin_endpoint_succeeds():
    client = boto3.client("mediapackage", region_name=region)
    origin_endpoint_config = _create_origin_endpoint_config()
    create_response = client.create_origin_endpoint(**origin_endpoint_config)
    list_response = client.list_origin_endpoints()
    # Before deletion
    origin_endpoints_list = list_response["OriginEndpoints"]
    client.delete_origin_endpoint(Id=create_response["Id"])
    # After deletion
    post_deletion_list_response = client.list_origin_endpoints()
    post_deletion_origin_endpoints_list = post_deletion_list_response["OriginEndpoints"]
    len(post_deletion_origin_endpoints_list).should.equal(
        len(origin_endpoints_list) - 1
    )


@mock_mediapackage
def test_update_origin_endpoint_succeeds():
    client = boto3.client("mediapackage", region_name=region)
    origin_endpoint_config = _create_origin_endpoint_config()
    create_response = client.create_origin_endpoint(**origin_endpoint_config)
    update_response = client.update_origin_endpoint(
        Id=create_response["Id"],
        Description="updated-channel-description",
        ManifestName="updated-manifest-name",
    )
    update_response["Description"].should.equal("updated-channel-description")
    update_response["ManifestName"].should.equal("updated-manifest-name")


@mock_mediapackage
def test_list_origin_endpoint_succeeds():
    origin_endpoints_list = []
    client = boto3.client("mediapackage", region_name=region)
    origin_endpoint_config = _create_origin_endpoint_config()
    len(origin_endpoints_list).should.equal(0)
    client.create_origin_endpoint(**origin_endpoint_config)
    list_response = client.list_origin_endpoints()
    origin_endpoints_list = list_response["OriginEndpoints"]
    len(origin_endpoints_list).should.equal(1)
    first_origin_endpoint = origin_endpoints_list[0]
    first_origin_endpoint["Arn"].should.equal(
        "arn:aws:mediapackage:origin_endpoint:{}".format(first_origin_endpoint["Id"])
    )
    first_origin_endpoint["ChannelId"].should.equal(origin_endpoint_config["ChannelId"])
    first_origin_endpoint["Description"].should.equal(
        origin_endpoint_config["Description"]
    )
    first_origin_endpoint["HlsPackage"].should.equal(
        origin_endpoint_config["HlsPackage"]
    )
    first_origin_endpoint["Origination"].should.equal("ALLOW")
