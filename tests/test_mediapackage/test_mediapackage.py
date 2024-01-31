import boto3
import pytest
from botocore.exceptions import ClientError  # Boto3 will always throw this exception

from moto import mock_aws

region = "eu-west-1"


def _create_channel_config(**kwargs):
    channel_id = kwargs.get("id", "channel-id")
    description = kwargs.get("description", "Awesome channel!")
    tags = kwargs.get("tags", {"Customer": "moto"})
    channel_config = dict(Description=description, Id=channel_id, Tags=tags)
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
    endpoint_id = kwargs.get("id", "origin-endpoint-id")
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
        Id=endpoint_id,
        ManifestName=manifest_name,
        MssPackage=mss_package,
        Origination=origination,
        StartoverWindowSeconds=startover_window_seconds,
        Tags=tags,
        TimeDelaySeconds=time_delay_seconds,
        Whitelist=whitelist,
    )
    return origin_endpoint_config


@mock_aws
def test_create_channel_succeeds():
    client = boto3.client("mediapackage", region_name=region)
    channel_config = _create_channel_config()

    channel = client.create_channel(**channel_config)
    assert channel["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert channel["Arn"] == f"arn:aws:mediapackage:channel:{channel['Id']}"
    assert channel["Description"] == "Awesome channel!"
    assert channel["Id"] == "channel-id"
    assert channel["Tags"]["Customer"] == "moto"


@mock_aws
def test_describe_channel_succeeds():
    client = boto3.client("mediapackage", region_name=region)
    channel_config = _create_channel_config()

    channel_id = client.create_channel(**channel_config)["Id"]
    channel = client.describe_channel(Id=channel_id)
    assert channel["Arn"] == f"arn:aws:mediapackage:channel:{channel['Id']}"
    assert channel["Description"] == channel_config["Description"]
    assert channel["Tags"]["Customer"] == "moto"


@mock_aws
def test_describe_unknown_channel_throws_error():
    client = boto3.client("mediapackage", region_name=region)
    channel_id = "unknown-channel"
    with pytest.raises(ClientError) as err:
        client.describe_channel(Id=channel_id)
    err = err.value.response["Error"]
    assert err["Code"] == "NotFoundException"
    assert err["Message"] == f"channel with id={channel_id} not found"


@mock_aws
def test_delete_unknown_channel_throws_error():
    client = boto3.client("mediapackage", region_name=region)
    channel_id = "unknown-channel"
    with pytest.raises(ClientError) as err:
        client.delete_channel(Id=channel_id)
    err = err.value.response["Error"]
    assert err["Code"] == "NotFoundException"
    assert err["Message"] == f"channel with id={channel_id} not found"


@mock_aws
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
    assert len(post_deletion_channels_list) == len(channels_list) - 1


@mock_aws
def test_list_channels_succeds():
    client = boto3.client("mediapackage", region_name=region)
    channel_config = _create_channel_config()

    client.create_channel(**channel_config)
    channels_list = client.list_channels()["Channels"]
    assert len(channels_list) == 1

    channel = channels_list[0]
    assert channel["Arn"] == f"arn:aws:mediapackage:channel:{channel['Id']}"
    assert channel["Description"] == channel_config["Description"]
    assert channel["Tags"]["Customer"] == "moto"


@mock_aws
def test_create_origin_endpoint_succeeds():
    client = boto3.client("mediapackage", region_name=region)
    origin_endpoint_config = _create_origin_endpoint_config()

    endpoint = client.create_origin_endpoint(**origin_endpoint_config)
    assert endpoint["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert endpoint["Arn"] == f"arn:aws:mediapackage:origin_endpoint:{endpoint['Id']}"
    assert endpoint["ChannelId"] == origin_endpoint_config["ChannelId"]
    assert endpoint["Description"] == origin_endpoint_config["Description"]
    assert endpoint["HlsPackage"] == origin_endpoint_config["HlsPackage"]
    assert endpoint["Origination"] == "ALLOW"


@mock_aws
def test_describe_origin_endpoint_succeeds():
    client = boto3.client("mediapackage", region_name=region)
    origin_endpoint_config = _create_origin_endpoint_config()

    endpoint_id = client.create_origin_endpoint(**origin_endpoint_config)["Id"]
    endpoint = client.describe_origin_endpoint(Id=endpoint_id)
    assert endpoint["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert endpoint["Arn"] == f"arn:aws:mediapackage:origin_endpoint:{endpoint['Id']}"
    assert endpoint["ChannelId"] == origin_endpoint_config["ChannelId"]
    assert endpoint["Description"] == origin_endpoint_config["Description"]
    assert endpoint["HlsPackage"] == origin_endpoint_config["HlsPackage"]
    assert endpoint["Origination"] == "ALLOW"
    assert (
        endpoint["Url"]
        == f"https://origin-endpoint.mediapackage.{region}.amazonaws.com/{endpoint['Id']}"
    )


@mock_aws
def test_describe_unknown_origin_endpoint_throws_error():
    client = boto3.client("mediapackage", region_name=region)
    channel_id = "unknown-channel"
    with pytest.raises(ClientError) as err:
        client.describe_origin_endpoint(Id=channel_id)
    err = err.value.response["Error"]
    assert err["Code"] == "NotFoundException"
    assert err["Message"] == f"origin endpoint with id={channel_id} not found"


@mock_aws
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
    assert len(post_deletion_origin_endpoints_list) == len(origin_endpoints_list) - 1


@mock_aws
def test_delete_unknown_origin_endpoint_throws_error():
    client = boto3.client("mediapackage", region_name=region)
    channel_id = "unknown-channel"
    with pytest.raises(ClientError) as err:
        client.delete_origin_endpoint(Id=channel_id)
    err = err.value.response["Error"]
    assert err["Code"] == "NotFoundException"
    assert err["Message"] == f"origin endpoint with id={channel_id} not found"


@mock_aws
def test_update_origin_endpoint_succeeds():
    client = boto3.client("mediapackage", region_name=region)
    origin_endpoint_config = _create_origin_endpoint_config()
    endpoint_id = client.create_origin_endpoint(**origin_endpoint_config)["Id"]

    endpoint = client.update_origin_endpoint(
        Id=endpoint_id,
        Description="updated-channel-description",
        ManifestName="updated-manifest-name",
    )
    assert endpoint["Description"] == "updated-channel-description"
    assert endpoint["ManifestName"] == "updated-manifest-name"


@mock_aws
def test_update_unknown_origin_endpoint_throws_error():
    client = boto3.client("mediapackage", region_name=region)
    channel_id = "unknown-channel"
    with pytest.raises(ClientError) as err:
        client.update_origin_endpoint(
            Id=channel_id,
            Description="updated-channel-description",
            ManifestName="updated-manifest-name",
        )
    err = err.value.response["Error"]
    assert err["Code"] == "NotFoundException"
    assert err["Message"] == f"origin endpoint with id={channel_id} not found"


@mock_aws
def test_list_origin_endpoint_succeeds():
    client = boto3.client("mediapackage", region_name=region)
    origin_endpoint_config = _create_origin_endpoint_config()

    client.create_origin_endpoint(**origin_endpoint_config)
    origin_endpoints_list = client.list_origin_endpoints()["OriginEndpoints"]
    assert len(origin_endpoints_list) == 1

    endpoint = origin_endpoints_list[0]
    assert endpoint["Arn"] == f"arn:aws:mediapackage:origin_endpoint:{endpoint['Id']}"
    assert endpoint["ChannelId"] == origin_endpoint_config["ChannelId"]
    assert endpoint["Description"] == origin_endpoint_config["Description"]
    assert endpoint["HlsPackage"] == origin_endpoint_config["HlsPackage"]
    assert endpoint["Origination"] == "ALLOW"
