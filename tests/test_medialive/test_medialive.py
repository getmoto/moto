from uuid import uuid4

import boto3

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

region = "eu-west-1"


def _create_input_config(name, **kwargs):
    role_arn = kwargs.get(
        "role_arn",
        f"arn:aws:iam::{ACCOUNT_ID}:role/TestMediaLiveInputCreateRole",
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
        f"arn:aws:iam::{ACCOUNT_ID}:role/TestMediaLiveChannelCreateRole",
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


@mock_aws
def test_create_channel_succeeds():
    client = boto3.client("medialive", region_name=region)
    channel_config = _create_channel_config("test channel 1")

    response = client.create_channel(**channel_config)
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    channel = response["Channel"]
    assert channel["Arn"] == f"arn:aws:medialive:channel:{response['Channel']['Id']}"
    assert channel["Destinations"] == channel_config["Destinations"]
    assert channel["EncoderSettings"] == channel_config["EncoderSettings"]
    assert channel["InputAttachments"] == channel_config["InputAttachments"]
    assert channel["Name"] == "test channel 1"
    assert channel["State"] == "CREATING"
    assert channel["Tags"]["Customer"] == "moto"


@mock_aws
def test_list_channels_succeeds():
    client = boto3.client("medialive", region_name=region)
    channel_configs = [
        _create_channel_config(f"test {idx}", request_id=f"req-{idx}")
        for idx in range(10)
    ]
    channel_configs[1]["ChannelClass"] = "SINGLE_PIPELINE"

    for config in channel_configs:
        client.create_channel(**config)

    response = client.list_channels()
    assert len(response["Channels"]) == 10

    assert response["Channels"][0]["Name"] == "test 0"
    assert response["Channels"][0]["ChannelClass"] == "STANDARD"
    assert response["Channels"][0]["PipelinesRunningCount"] == 2

    assert response["Channels"][1]["Name"] == "test 1"
    assert response["Channels"][1]["ChannelClass"] == "SINGLE_PIPELINE"
    assert response["Channels"][1]["PipelinesRunningCount"] == 1

    page1 = client.list_channels(MaxResults=2)
    assert len(page1["Channels"]) == 2
    channel_names = [c["Name"] for c in page1["Channels"]]
    assert ["test 0", "test 1"] == sorted(channel_names)

    page2 = client.list_channels(MaxResults=5, NextToken=page1["NextToken"])
    assert len(page2["Channels"]) == 5
    channel_names = [c["Name"] for c in page2["Channels"]]
    assert ["test 2", "test 3", "test 4", "test 5", "test 6"] == sorted(channel_names)

    page3 = client.list_channels(NextToken=page2["NextToken"])
    assert len(page3["Channels"]) == 3
    channel_names = [c["Name"] for c in page3["Channels"]]
    assert ["test 7", "test 8", "test 9"] == sorted(channel_names)


@mock_aws
def test_delete_channel_moves_channel_in_deleted_state():
    client = boto3.client("medialive", region_name=region)
    channel_name = "test channel X"
    channel_config = _create_channel_config(channel_name)

    channel_id = client.create_channel(**channel_config)["Channel"]["Id"]
    delete_response = client.delete_channel(ChannelId=channel_id)

    assert delete_response["Name"] == channel_name
    assert delete_response["State"] == "DELETING"


@mock_aws
def test_describe_channel_succeeds():
    client = boto3.client("medialive", region_name=region)
    channel_name = "test channel X"
    channel_config = _create_channel_config(channel_name)

    channel_id = client.create_channel(**channel_config)["Channel"]["Id"]
    channel = client.describe_channel(ChannelId=channel_id)

    assert channel["Arn"] == f"arn:aws:medialive:channel:{channel['Id']}"
    assert channel["Destinations"] == channel_config["Destinations"]
    assert channel["EncoderSettings"] == channel_config["EncoderSettings"]
    assert channel["InputAttachments"] == channel_config["InputAttachments"]
    assert channel["Name"] == channel_name
    assert channel["State"] == "IDLE"
    assert channel["Tags"]["Customer"] == "moto"


@mock_aws
def test_start_channel_succeeds():
    client = boto3.client("medialive", region_name=region)
    channel_name = "testchan1"
    channel_config = _create_channel_config(channel_name)

    channel_id = client.create_channel(**channel_config)["Channel"]["Id"]
    start_response = client.start_channel(ChannelId=channel_id)
    assert start_response["Name"] == channel_name
    assert start_response["State"] == "STARTING"

    assert client.describe_channel(ChannelId=channel_id)["State"] == "RUNNING"


@mock_aws
def test_stop_channel_succeeds():
    client = boto3.client("medialive", region_name=region)
    channel_name = "testchan2"
    channel_config = _create_channel_config(channel_name)

    channel_id = client.create_channel(**channel_config)["Channel"]["Id"]
    assert len(channel_id) > 1
    client.start_channel(ChannelId=channel_id)
    stop_response = client.stop_channel(ChannelId=channel_id)
    assert stop_response["Name"] == channel_name
    assert stop_response["State"] == "STOPPING"

    assert client.describe_channel(ChannelId=channel_id)["State"] == "IDLE"


@mock_aws
def test_update_channel_succeeds():
    client = boto3.client("medialive", region_name=region)
    channel_name = "Original Channel"
    channel_config = _create_channel_config(channel_name)

    channel_id = client.create_channel(**channel_config)["Channel"]["Id"]

    updated_channel = client.update_channel(
        ChannelId=channel_id, Name="Updated Channel"
    )["Channel"]
    assert updated_channel["State"] == "UPDATING"
    assert updated_channel["Name"] == "Updated Channel"

    channel = client.describe_channel(ChannelId=channel_id)
    assert channel["State"] == "IDLE"
    assert channel["Name"] == "Updated Channel"


@mock_aws
def test_create_input_succeeds():
    client = boto3.client("medialive", region_name=region)
    input_name = "Input One"
    input_config = _create_input_config(input_name)

    create_response = client.create_input(**input_config)
    assert create_response["ResponseMetadata"]["HTTPStatusCode"] == 200
    r_input = create_response["Input"]
    input_id = r_input["Id"]
    assert len(input_id) > 1
    assert r_input["Arn"] == f"arn:aws:medialive:input:{r_input['Id']}"
    assert r_input["Name"] == input_name
    assert r_input["AttachedChannels"] == []
    assert r_input["Destinations"] == input_config["Destinations"]
    assert r_input["InputClass"] == "STANDARD"
    assert r_input["InputDevices"] == input_config["InputDevices"]
    assert r_input["InputSourceType"] == "STATIC"
    assert r_input["MediaConnectFlows"] == input_config["MediaConnectFlows"]
    assert r_input["RoleArn"] == input_config["RoleArn"]
    assert r_input["SecurityGroups"] == []
    assert r_input["Sources"] == input_config["Sources"]
    assert r_input["State"] == "CREATING"
    assert r_input["Tags"] == input_config["Tags"]
    assert r_input["Type"] == input_config["Type"]


@mock_aws
def test_describe_input_succeeds():
    client = boto3.client("medialive", region_name=region)
    input_name = "Input Two"
    input_config = _create_input_config(input_name)

    create_response = client.create_input(**input_config)
    assert create_response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert create_response["Input"]["State"] == "CREATING"

    describe_response = client.describe_input(InputId=create_response["Input"]["Id"])
    assert describe_response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert describe_response["Name"] == input_name
    assert describe_response["State"] == "DETACHED"
    assert describe_response["MediaConnectFlows"] == input_config["MediaConnectFlows"]


@mock_aws
def test_list_inputs_succeeds():
    client = boto3.client("medialive", region_name=region)
    configs = [_create_input_config(f"Input {idx}") for idx in range(10)]
    for config in configs:
        client.create_input(**config)

    inputs = client.list_inputs()["Inputs"]
    assert len(inputs) == 10

    page1 = client.list_inputs(MaxResults=2)
    assert len(page1["Inputs"]) == 2
    names = [i["Name"] for i in page1["Inputs"]]
    assert sorted(names) == ["Input 0", "Input 1"]

    page2 = client.list_inputs(MaxResults=5, NextToken=page1["NextToken"])
    assert len(page2["Inputs"]) == 5
    names = [i["Name"] for i in page2["Inputs"]]
    assert sorted(names) == ["Input 2", "Input 3", "Input 4", "Input 5", "Input 6"]

    page3 = client.list_inputs(NextToken=page2["NextToken"])
    assert len(page3["Inputs"]) == 3
    names = [i["Name"] for i in page3["Inputs"]]
    assert sorted(names) == ["Input 7", "Input 8", "Input 9"]


@mock_aws
def test_delete_input_moves_input_in_deleted_state():
    client = boto3.client("medialive", region_name=region)
    input_name = "test input X"
    input_config = _create_input_config(input_name)

    input_id = client.create_input(**input_config)["Input"]["Id"]
    response = client.delete_input(InputId=input_id)
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    input_ = client.describe_input(InputId=input_id)
    assert input_["Name"] == input_name
    assert input_["State"] == "DELETED"


@mock_aws
def test_update_input_succeeds():
    client = boto3.client("medialive", region_name=region)
    input_name = "test input X"
    input_config = _create_input_config(input_name)

    input_id = client.create_input(**input_config)["Input"]["Id"]
    input_ = client.update_input(InputId=input_id, Name="test input U")
    assert input_["Input"]["Name"] == "test input U"
