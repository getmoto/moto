from re import fullmatch

import boto3
from botocore.exceptions import ClientError
from pytest import raises

from moto import mock_aws


@mock_aws
def test_create_channel_with_name():
    client = boto3.client("ivs", region_name="eu-west-1")
    create_response = client.create_channel(name="foo")
    assert create_response["channel"]["name"] == "foo"


@mock_aws
def test_create_channel_defaults():
    client = boto3.client("ivs", region_name="eu-west-1")
    create_response = client.create_channel(name="foo")
    assert create_response["channel"]["authorized"] is False
    assert create_response["channel"]["insecureIngest"] is False
    assert create_response["channel"]["latencyMode"] == "LOW"
    assert create_response["channel"]["preset"] == ""
    assert create_response["channel"]["recordingConfigurationArn"] == ""
    assert create_response["channel"]["tags"] == {}
    assert create_response["channel"]["type"] == "STANDARD"
    assert create_response["streamKey"]["tags"] == {}


@mock_aws
def test_create_channel_generated_values():
    client = boto3.client("ivs", region_name="eu-west-1")
    create_response = client.create_channel(name="foo")
    assert fullmatch(r"arn:aws:ivs:.*:channel/.*", create_response["channel"]["arn"])
    assert create_response["channel"]["ingestEndpoint"]
    assert create_response["channel"]["playbackUrl"]
    assert fullmatch(
        r"arn:aws:ivs:.*:stream-key/.*", create_response["streamKey"]["arn"]
    )
    assert (
        create_response["streamKey"]["channelArn"] == create_response["channel"]["arn"]
    )
    assert fullmatch(r"sk_.*", create_response["streamKey"]["value"])


@mock_aws
def test_create_channel_with_name_and_recording_configuration():
    client = boto3.client("ivs", region_name="eu-west-1")
    create_response = client.create_channel(
        name="foo",
        recordingConfigurationArn="blah",
    )
    assert create_response["channel"]["name"] == "foo"
    assert create_response["channel"]["recordingConfigurationArn"] == "blah"


@mock_aws
def test_list_channels_empty():
    client = boto3.client("ivs", region_name="eu-west-1")
    list_response = client.list_channels()
    assert list_response["channels"] == []


@mock_aws
def test_list_channels_one():
    client = boto3.client("ivs", region_name="eu-west-1")
    client.create_channel(name="foo")
    list_response = client.list_channels()
    assert len(list_response["channels"]) == 1
    assert list_response["channels"][0]["name"] == "foo"


@mock_aws
def test_list_channels_two():
    client = boto3.client("ivs", region_name="eu-west-1")
    client.create_channel(name="foo")
    client.create_channel(
        name="bar",
        recordingConfigurationArn="blah",
    )
    list_response = client.list_channels()
    assert len(list_response["channels"]) == 2
    assert list_response["channels"][0]["name"] == "foo"
    assert list_response["channels"][1]["name"] == "bar"


@mock_aws
def test_list_channels_by_name():
    client = boto3.client("ivs", region_name="eu-west-1")
    client.create_channel(name="foo")
    client.create_channel(
        name="bar",
        recordingConfigurationArn="blah",
    )
    list_response = client.list_channels(filterByName="foo")
    assert len(list_response["channels"]) == 1
    assert list_response["channels"][0]["name"] == "foo"


@mock_aws
def test_list_channels_by_recording_configuration():
    client = boto3.client("ivs", region_name="eu-west-1")
    client.create_channel(name="foo")
    client.create_channel(
        name="bar",
        recordingConfigurationArn="blah",
    )
    list_response = client.list_channels(filterByRecordingConfigurationArn="blah")
    assert len(list_response["channels"]) == 1
    assert list_response["channels"][0]["name"] == "bar"


@mock_aws
def test_list_channels_pagination():
    client = boto3.client("ivs", region_name="eu-west-1")
    client.create_channel(name="foo")
    client.create_channel(name="bar")
    first_list_response = client.list_channels(maxResults=1)
    assert len(first_list_response["channels"]) == 1
    assert "nextToken" in first_list_response
    second_list_response = client.list_channels(
        maxResults=1, nextToken=first_list_response["nextToken"]
    )
    assert len(second_list_response["channels"]) == 1
    assert "nextToken" not in second_list_response


@mock_aws
def test_get_channel_exists():
    client = boto3.client("ivs", region_name="eu-west-1")
    create_response = client.create_channel(name="foo")
    get_response = client.get_channel(arn=create_response["channel"]["arn"])
    assert get_response["channel"]["name"] == "foo"


@mock_aws
def test_get_channel_not_exists():
    client = boto3.client("ivs", region_name="eu-west-1")
    with raises(ClientError) as exc:
        client.get_channel(arn="nope")
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_batch_get_channel():
    client = boto3.client("ivs", region_name="eu-west-1")
    create_response = client.create_channel(name="foo")
    batch_get_response = client.batch_get_channel(
        arns=[create_response["channel"]["arn"]]
    )
    assert len(batch_get_response["channels"]) == 1
    assert batch_get_response["channels"][0]["name"] == "foo"


@mock_aws
def test_update_channel_exists():
    client = boto3.client("ivs", region_name="eu-west-1")
    create_response = client.create_channel(
        name="foo",
        recordingConfigurationArn="blah",
    )
    update_response = client.update_channel(
        arn=create_response["channel"]["arn"],
        name="bar",
    )
    assert update_response["channel"]["name"] == "bar"
    assert update_response["channel"]["recordingConfigurationArn"] == "blah"


@mock_aws
def test_update_channel_not_exists():
    client = boto3.client("ivs", region_name="eu-west-1")
    with raises(ClientError) as exc:
        client.update_channel(arn="nope", name="bar")
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_delete_channel_exists():
    client = boto3.client("ivs", region_name="eu-west-1")
    create_response = client.create_channel(name="foo")
    client.delete_channel(arn=create_response["channel"]["arn"])
    list_response = client.list_channels()
    assert list_response["channels"] == []


@mock_aws
def test_delete_channel_not_exists():
    client = boto3.client("ivs", region_name="eu-west-1")
    with raises(ClientError) as exc:
        client.delete_channel(arn="nope")
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"
