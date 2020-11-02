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
