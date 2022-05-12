import boto3
import sure  # noqa # pylint: disable=unused-import
from moto import mock_medialive
from uuid import uuid4

from moto.core import ACCOUNT_ID

region = "eu-west-1"


def _create_input_config(name, **kwargs):
    role_arn = kwargs.get(
        "role_arn",
        "arn:aws:iam::{}:role/TestMediaLiveInputCreateRole".format(ACCOUNT_ID),
    )
    input_type = kwargs.get("type", "RTP_PUSH")
    request_id = kwargs.get("request_id", uuid4().hex)
    destinations = kwargs.get("destinations", [])
    input_devices = kwargs.get("input_devices", [{"Id": "1234-56"}])
    input_security_groups = ["123456"]
    media_connect_flows = kwargs.get("media_connect_flows", [{"FlowArn": "flow:1"}])
    sources = kwargs.get(
        "sources",
        [
            {
                "PasswordParam": "pwd431$%!",
                "Url": "scheme://url:1234/",
                "Username": "userX",
            }
        ],
    )
    tags = kwargs.get("tags", {"Customer": "moto"})
    vpc_config = kwargs.get(
        "vpc", {"SubnetIds": ["subnet-1"], "SecurityGroupIds": ["sg-0001"]}
    )
    input_config = dict(
        Name=name,
        Destinations=destinations,
        InputDevices=input_devices,
        InputSecurityGroups=input_security_groups,
        MediaConnectFlows=media_connect_flows,
        RoleArn=role_arn,
        RequestId=request_id,
        Sources=sources,
        Type=input_type,
        Tags=tags,
        Vpc=vpc_config,
    )
    return input_config


def _create_channel_config(name, **kwargs):
    role_arn = kwargs.get(
        "role_arn",
        "arn:aws:iam::{}:role/TestMediaLiveChannelCreateRole".format(ACCOUNT_ID),
    )
    input_id = kwargs.get("input_id", "an-attachment-id")
    input_settings = kwargs.get(
        "input_settings",
        [
            {
                "InputId": input_id,
                "InputSettings": {
                    "DenoiseFilter": "DISABLED",
                    "AudioSelectors": [
                        {"Name": "EnglishLanguage", "SelectorSettings": {}}
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
            "TimecodeConfig": {"Source": "a-source"},
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


@mock_medialive
def test_delete_channel_moves_channel_in_deleted_state():
    client = boto3.client("medialive", region_name=region)
    channel_name = "test channel X"
    channel_config = _create_channel_config(channel_name)

    create_response = client.create_channel(**channel_config)
    delete_response = client.delete_channel(ChannelId=create_response["Channel"]["Id"])

    delete_response["Name"].should.equal(channel_name)
    delete_response["State"].should.equal("DELETING")


@mock_medialive
def test_describe_channel_succeeds():
    client = boto3.client("medialive", region_name=region)
    channel_name = "test channel X"
    channel_config = _create_channel_config(channel_name)

    create_response = client.create_channel(**channel_config)
    describe_response = client.describe_channel(
        ChannelId=create_response["Channel"]["Id"]
    )

    describe_response["Arn"].should.equal(
        "arn:aws:medialive:channel:{}".format(describe_response["Id"])
    )
    describe_response["Destinations"].should.equal(channel_config["Destinations"])
    describe_response["EncoderSettings"].should.equal(channel_config["EncoderSettings"])
    describe_response["InputAttachments"].should.equal(
        channel_config["InputAttachments"]
    )
    describe_response["Name"].should.equal(channel_name)
    describe_response["State"].should.equal("IDLE")
    describe_response["Tags"]["Customer"].should.equal("moto")


@mock_medialive
def test_start_channel_succeeds():
    client = boto3.client("medialive", region_name=region)
    channel_name = "testchan1"
    channel_config = _create_channel_config(channel_name)

    create_response = client.create_channel(**channel_config)
    start_response = client.start_channel(ChannelId=create_response["Channel"]["Id"])
    start_response["Name"].should.equal(channel_name)
    start_response["State"].should.equal("STARTING")

    describe_response = client.describe_channel(
        ChannelId=create_response["Channel"]["Id"]
    )
    describe_response["State"].should.equal("RUNNING")


@mock_medialive
def test_stop_channel_succeeds():
    client = boto3.client("medialive", region_name=region)
    channel_name = "testchan2"
    channel_config = _create_channel_config(channel_name)

    create_response = client.create_channel(**channel_config)
    channel_id = create_response["Channel"]["Id"]
    assert len(channel_id) > 1
    client.start_channel(ChannelId=channel_id)
    stop_response = client.stop_channel(ChannelId=channel_id)
    stop_response["Name"].should.equal(channel_name)
    stop_response["State"].should.equal("STOPPING")

    describe_response = client.describe_channel(
        ChannelId=create_response["Channel"]["Id"]
    )
    describe_response["State"].should.equal("IDLE")


@mock_medialive
def test_update_channel_succeeds():
    client = boto3.client("medialive", region_name=region)
    channel_name = "Original Channel"
    channel_config = _create_channel_config(channel_name)

    create_response = client.create_channel(**channel_config)
    channel_id = create_response["Channel"]["Id"]
    assert len(channel_id) > 1

    update_response = client.update_channel(
        ChannelId=channel_id, Name="Updated Channel"
    )
    update_response["Channel"]["State"].should.equal("UPDATING")
    update_response["Channel"]["Name"].should.equal("Updated Channel")

    describe_response = client.describe_channel(ChannelId=channel_id)
    describe_response["State"].should.equal("IDLE")
    describe_response["Name"].should.equal("Updated Channel")


@mock_medialive
def test_create_input_succeeds():
    client = boto3.client("medialive", region_name=region)
    input_name = "Input One"
    input_config = _create_input_config(input_name)

    create_response = client.create_input(**input_config)
    create_response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    r_input = create_response["Input"]
    input_id = r_input["Id"]
    assert len(input_id) > 1
    r_input["Arn"].should.equal("arn:aws:medialive:input:{}".format(r_input["Id"]))
    r_input["Name"].should.equal(input_name)
    r_input["AttachedChannels"].should.equal([])
    r_input["Destinations"].should.equal(input_config["Destinations"])
    r_input["InputClass"].should.equal("STANDARD")
    r_input["InputDevices"].should.equal(input_config["InputDevices"])
    r_input["InputSourceType"].should.equal("STATIC")
    r_input["MediaConnectFlows"].should.equal(input_config["MediaConnectFlows"])
    r_input["RoleArn"].should.equal(input_config["RoleArn"])
    r_input["SecurityGroups"].should.equal([])
    r_input["Sources"].should.equal(input_config["Sources"])
    r_input["State"].should.equal("CREATING")
    r_input["Tags"].should.equal(input_config["Tags"])
    r_input["Type"].should.equal(input_config["Type"])


@mock_medialive
def test_describe_input_succeeds():
    client = boto3.client("medialive", region_name=region)
    input_name = "Input Two"
    input_config = _create_input_config(input_name)

    create_response = client.create_input(**input_config)
    create_response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    create_response["Input"]["State"].should.equal("CREATING")

    describe_response = client.describe_input(InputId=create_response["Input"]["Id"])
    describe_response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    describe_response["Name"].should.equal(input_name)
    describe_response["State"].should.equal("DETACHED")
    describe_response["MediaConnectFlows"].should.equal(
        input_config["MediaConnectFlows"]
    )


@mock_medialive
def test_list_inputs_succeeds():
    client = boto3.client("medialive", region_name=region)
    input_config1 = _create_input_config("Input One")
    client.create_input(**input_config1)
    input_config2 = _create_input_config("Input Two")
    client.create_input(**input_config2)

    response = client.list_inputs()
    len(response["Inputs"]).should.equal(2)

    response["Inputs"][0]["Name"].should.equal("Input One")
    response["Inputs"][1]["Name"].should.equal("Input Two")


@mock_medialive
def test_delete_input_moves_input_in_deleted_state():
    client = boto3.client("medialive", region_name=region)
    input_name = "test input X"
    input_config = _create_input_config(input_name)

    create_response = client.create_input(**input_config)
    delete_response = client.delete_input(InputId=create_response["Input"]["Id"])
    delete_response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    describe_response = client.describe_input(InputId=create_response["Input"]["Id"])
    describe_response["Name"].should.equal(input_name)
    describe_response["State"].should.equal("DELETED")


@mock_medialive
def test_update_input_succeeds():
    client = boto3.client("medialive", region_name=region)
    input_name = "test input X"
    input_config = _create_input_config(input_name)

    create_response = client.create_input(**input_config)
    update_response = client.update_input(
        InputId=create_response["Input"]["Id"], Name="test input U"
    )
    update_response["Input"]["Name"].should.equal("test input U")
