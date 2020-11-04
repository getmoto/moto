from __future__ import unicode_literals

import boto3
import sure  # noqa
from moto import mock_medialive

region = "eu-west-1"


def _create_channel_config(name, **kwargs):
    role_arn = kwargs.get(
        "role_arn", "arn:aws:iam::123456789012:role/TestMediaLiveChannelCreateRole"
    )
    input_settings = kwargs.get(
        "input_settings",
        [
            {
                "InputId": "an-attachment-id",
                "InputSettings": {
                    "DenoiseFilter": "DISABLED",
                    "AudioSelectors": [
                        {"Name": "EnglishLanguage", "SelectorSettings": {},}
                    ],
                    "InputFilter": "AUTO",
                    "DeblockFilter": "DISABLED",
                    "NetworkInputSettings": {
                        "ServerValidation": "CHECK_CRYPTOGRAPHY_AND_VALIDATE_NAME",
                    },
                    "SourceEndBehavior": "CONTINUE",
                    "FilterStrength": 1,
                },
            }
        ],
    )
    destinations = kwargs.get(
        "destinations", [{"Id": "destination.1"}, {"Id": "destination.2"}]
    )
    encoder_settings = kwargs.get(
        "encoder_settings",
        {
            "VideoDescriptions": [],
            "AudioDescriptions": [],
            "OutputGroups": [],
            "TimecodeConfig": {"Source": "a-source",},
        },
    )
    input_specification = kwargs.get("input_specification", {})
    log_level = kwargs.get("log_level", "INFO")
    tags = kwargs.get("tags", {"Customer": "moto"})
    channel_config = dict(
        Name=name,
        RoleArn=role_arn,
        InputAttachments=input_settings,
        Destinations=destinations,
        EncoderSettings=encoder_settings,
        InputSpecification=input_specification,
        RequestId=name,
        LogLevel=log_level,
        Tags=tags,
    )
    return channel_config


@mock_medialive
def test_create_channel_succeeds():
    client = boto3.client("medialive", region_name=region)
    channel_config = _create_channel_config("test channel 1")

    response = client.create_channel(**channel_config)

    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    response["Channel"]["Arn"].should.equal(
        "arn:aws:medialive:channel:{}".format(response["Channel"]["Id"])
    )
    response["Channel"]["Destinations"].should.equal(channel_config["Destinations"])
    response["Channel"]["EncoderSettings"].should.equal(
        channel_config["EncoderSettings"]
    )
    response["Channel"]["InputAttachments"].should.equal(
        channel_config["InputAttachments"]
    )
    response["Channel"]["Name"].should.equal("test channel 1")
    response["Channel"]["State"].should.equal("CREATING")
    response["Channel"]["Tags"]["Customer"].should.equal("moto")


@mock_medialive
def test_list_channels_succeeds():
    client = boto3.client("medialive", region_name=region)
    channel1_config = _create_channel_config("test channel 1", request_id="request-1")
    channel2_config = _create_channel_config("test channel 2", request_id="request-2")
    channel2_config["ChannelClass"] = "SINGLE_PIPELINE"

    client.create_channel(**channel1_config)
    client.create_channel(**channel2_config)

    response = client.list_channels()
    len(response["Channels"]).should.equal(2)

    response["Channels"][0]["Name"].should.equal("test channel 1")
    response["Channels"][0]["ChannelClass"].should.equal("STANDARD")
    response["Channels"][0]["PipelinesRunningCount"].should.equal(2)

    response["Channels"][1]["Name"].should.equal("test channel 2")
    response["Channels"][1]["ChannelClass"].should.equal("SINGLE_PIPELINE")
    response["Channels"][1]["PipelinesRunningCount"].should.equal(1)

    #    {
    #        'Arn': 'arn:aws:medialive:channel:3de9479667bd4f9ab1d7f4819cb426d8',
    #        'ChannelClass': 'STANDARD',
    #        'Destinations': [{'Id': 'destination.1'}, {'Id': 'destination.2'}],
    #        'EgressEndpoints': [],
    #        'Id': '3de9479667bd4f9ab1d7f4819cb426d8',
    #        'InputAttachments': [{'InputId': 'an-attachment-id', 'InputSettings': {'AudioSelectors': [{'Name': 'EnglishLanguage', 'SelectorSettings': {}}], 'DeblockFilter': 'DISABLED', 'DenoiseFilter': 'DISABLED', 'FilterStrength': 1, 'InputFilter': 'AUTO', 'NetworkInputSettings': {'ServerValidation': 'CHECK_CRYPTOGRAPHY_AND_VALIDATE_NAME'}, 'SourceEndBehavior': 'CONTINUE'}}],
    #        'InputSpecification': {},
    #        'LogLevel': 'INFO',
    #        'Name': 'test channel 1',
    #        'PipelinesRunningCount': 2,
    #        'RoleArn': 'arn:aws:iam::123456789012:role/TestMediaLiveChannelCreateRole',
    #        'State': 'CREATING',
    #        'Tags': {'ChannelID': 'test-channel-1', 'Customer': 'moto'}},
    #    {
    #        'Arn': 'arn:aws:medialive:channel:4a1da47c5c894bfe8beb3d678b414401',
    #        'ChannelClass': 'SINGLE_PIPELINE',
    #        'Destinations': [{'Id': 'destination.1'}, {'Id': 'destination.2'}],
    #        'EgressEndpoints': [],
    #        'Id': '4a1da47c5c894bfe8beb3d678b414401',
    #        'InputAttachments': [{'InputId': 'an-attachment-id', 'InputSettings': {'AudioSelectors': [{'Name': 'EnglishLanguage', 'SelectorSettings': {}}], 'DeblockFilter': 'DISABLED', 'DenoiseFilter': 'DISABLED', 'FilterStrength': 1, 'InputFilter': 'AUTO', 'NetworkInputSettings': {'ServerValidation': 'CHECK_CRYPTOGRAPHY_AND_VALIDATE_NAME'}, 'SourceEndBehavior': 'CONTINUE'}}],
    #        'InputSpecification': {},
    #        'LogLevel': 'INFO',
    #        'Name': 'test channel 2',
    #        'PipelinesRunningCount': 1,
    #        'RoleArn': 'arn:aws:iam::123456789012:role/TestMediaLiveChannelCreateRole',
    #        'State': 'CREATING',
    #        'Tags': {'ChannelID': 'test-channel-1', 'Customer': 'moto'}
    #    }


@mock_medialive
def test_delete_channel_moves_channel_in_deleted_state():
    client = boto3.client("medialive", region_name=region)
    channel_name = "test channel X"
    channel_config = _create_channel_config(channel_name)

    create_response = client.create_channel(**channel_config)
    delete_response = client.delete_channel(ChannelId=create_response["Channel"]["Id"])

    delete_response["Name"].should.equal(channel_name)
    delete_response["State"].should.equal("DELETED")
