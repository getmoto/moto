from __future__ import unicode_literals

import boto3
import sure  # noqa
from moto import mock_medialive

region = "eu-west-1"


@mock_medialive
def test_create_channel_succeeds():
    client = boto3.client("medialive", region_name=region)
    name = "test channel 1"
    role_arn = "arn:aws:iam::123456789012:role/TestMediaLiveChannelCreateRole"
    input_settings = [
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
    ]
    destinations = [{"Id": "destination.1"}, {"Id": "destination.2"}]
    encoder_settings = {
        "VideoDescriptions": [],
        "AudioDescriptions": [],
        "OutputGroups": [],
        "TimecodeConfig": {"Source": "a-source",},
    }
    input_specification = {}
    log_level = "INFO"
    tags = {"ChannelID": "test-channel-1", "Customer": "moto"}

    response = client.create_channel(
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

    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    response["Channel"]["Arn"].should.equal(
        "arn:aws:medialive:channel:{}".format(response["Channel"]["Id"])
    )
    response["Channel"]["Destinations"].should.equal(destinations)
    response["Channel"]["EncoderSettings"].should.equal(encoder_settings)
    response["Channel"]["InputAttachments"].should.equal(input_settings)
    response["Channel"]["Name"].should.equal(name)
    response["Channel"]["State"].should.equal("CREATING")
    response["Channel"]["Tags"]["Customer"].should.equal("moto")


@mock_medialive
def test_list_channels_succeeds():
    client = boto3.client("medialive", region_name=region)
    role_arn = "arn:aws:iam::123456789012:role/TestMediaLiveChannelCreateRole"
    input_settings = [
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
    ]
    destinations = [{"Id": "destination.1"}, {"Id": "destination.2"}]
    encoder_settings = {
        "VideoDescriptions": [],
        "AudioDescriptions": [],
        "OutputGroups": [],
        "TimecodeConfig": {"Source": "a-source",},
    }
    input_specification = {}
    log_level = "INFO"
    tags = {"ChannelID": "test-channel-1", "Customer": "moto"}

    client.create_channel(
        Name="test channel 1",
        RoleArn=role_arn,
        InputAttachments=input_settings,
        Destinations=destinations,
        EncoderSettings=encoder_settings,
        InputSpecification=input_specification,
        RequestId="request-1",
        LogLevel=log_level,
        Tags=tags,
    )

    client.create_channel(
        Name="test channel 2",
        ChannelClass="SINGLE_PIPELINE",
        RoleArn=role_arn,
        InputAttachments=input_settings,
        Destinations=destinations,
        EncoderSettings=encoder_settings,
        InputSpecification=input_specification,
        RequestId="request-2",
        LogLevel=log_level,
        Tags=tags,
    )

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
