from uuid import UUID

import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import
from botocore.exceptions import ClientError

from moto import mock_mediaconnect
from moto.core import ACCOUNT_ID

region = "eu-west-1"


def _source(name="Source-A"):
    return {
        "Decryption": {"Algorithm": "aes256", "RoleArn": "some:role"},
        "Description": "A source",
        "Name": name,
    }


def _create_flow_config(name, **kwargs):
    availability_zone = kwargs.get("availability_zone", "AZ1")
    entitlements = kwargs.get(
        "entitlements",
        [
            {
                "DataTransferSubscriberFeePercent": 12,
                "Description": "An entitlement",
                "Encryption": {"Algorithm": "aes256", "RoleArn": "some:role"},
                "EntitlementStatus": "ENABLED",
                "Name": "Entitlement-A",
                "Subscribers": [],
            }
        ],
    )
    outputs = kwargs.get(
        "outputs",
        [
            {"Name": "Output-1", "Protocol": "zixi-push"},
            {"Name": "Output-2", "Protocol": "zixi-pull"},
            {"Name": "Output-3", "Protocol": "srt-listener"},
        ],
    )
    source = kwargs.get(
        "source",
        _source(),
    )
    source_failover_config = kwargs.get("source_failover_config", {})
    sources = kwargs.get("sources", [])
    vpc_interfaces = kwargs.get("vpc_interfaces", [])
    flow_config = dict(Name=name)
    optional_flow_config = dict(
        AvailabilityZone=availability_zone,
        Entitlements=entitlements,
        Outputs=outputs,
        Source=source,
        SourceFailoverConfig=source_failover_config,
        Sources=sources,
        VpcInterfaces=vpc_interfaces,
    )
    for key, value in optional_flow_config.items():
        if value:
            flow_config[key] = value
    return flow_config


def _check_mediaconnect_arn(type_, arn, name):
    _arn_list = str.split(arn, ":")
    _arn_list[:6].should.equal(
        ["arn", "aws", "mediaconnect", region, ACCOUNT_ID, type_]
    )
    UUID(_arn_list[6])
    _arn_list[-1].should.equal(name)


@mock_mediaconnect
def test_create_flow_succeeds():
    client = boto3.client("mediaconnect", region_name=region)
    channel_config = _create_flow_config("test-Flow-1")

    response = client.create_flow(**channel_config)

    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    _check_mediaconnect_arn(
        type_="flow", arn=response["Flow"]["FlowArn"], name="test-Flow-1"
    )
    response["Flow"]["Name"].should.equal("test-Flow-1")
    response["Flow"]["Status"].should.equal("STANDBY")
    response["Flow"]["Outputs"][0].should.equal({"Name": "Output-1"})
    response["Flow"]["Outputs"][1]["ListenerAddress"].should.equal("1.0.0.0")
    response["Flow"]["Outputs"][2]["ListenerAddress"].should.equal("2.0.0.0")
    response["Flow"]["Source"]["IngestIp"].should.equal("127.0.0.0")
    _check_mediaconnect_arn(
        type_="source", arn=response["Flow"]["Sources"][0]["SourceArn"], name="Source-A"
    )


@mock_mediaconnect
def test_create_flow_alternative_succeeds():
    client = boto3.client("mediaconnect", region_name=region)
    channel_config = _create_flow_config(
        "test-Flow-1",
        source=None,
        sources=[_source(), _source("Source-B")],
        source_failover_config={
            "FailoverMode": "FAILOVER",
            "SourcePriority": {"PrimarySource": "Source-B"},
            "State": "ENABLED",
        },
        outputs=None,
    )

    response = client.create_flow(**channel_config)

    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    _check_mediaconnect_arn(
        type_="flow", arn=response["Flow"]["FlowArn"], name="test-Flow-1"
    )
    response["Flow"]["Name"].should.equal("test-Flow-1")
    response["Flow"]["Status"].should.equal("STANDBY")
    response["Flow"]["Sources"][0]["IngestIp"].should.equal("127.0.0.0")
    response["Flow"]["Sources"][1]["IngestIp"].should.equal("127.0.0.1")
    _check_mediaconnect_arn(
        type_="source", arn=response["Flow"]["Sources"][0]["SourceArn"], name="Source-A"
    )


@mock_mediaconnect
def test_list_flows_succeeds():
    client = boto3.client("mediaconnect", region_name=region)
    flow_1_config = _create_flow_config("test-Flow-1")
    flow_2_config = _create_flow_config("test-Flow-2")

    client.create_flow(**flow_1_config)
    client.create_flow(**flow_2_config)

    response = client.list_flows()
    len(response["Flows"]).should.equal(2)

    response["Flows"][0]["Name"].should.equal("test-Flow-1")
    response["Flows"][0]["AvailabilityZone"].should.equal("AZ1")
    response["Flows"][0]["SourceType"].should.equal("OWNED")
    response["Flows"][0]["Status"].should.equal("STANDBY")

    response["Flows"][1]["Name"].should.equal("test-Flow-2")
    response["Flows"][1]["AvailabilityZone"].should.equal("AZ1")
    response["Flows"][1]["SourceType"].should.equal("OWNED")
    response["Flows"][1]["Status"].should.equal("STANDBY")


@mock_mediaconnect
def test_describe_flow_succeeds():
    client = boto3.client("mediaconnect", region_name=region)
    channel_config = _create_flow_config("test-Flow-1")

    create_response = client.create_flow(**channel_config)
    create_response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    flow_arn = create_response["Flow"]["FlowArn"]
    describe_response = client.describe_flow(FlowArn=flow_arn)
    describe_response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    describe_response["Flow"]["Name"].should.equal("test-Flow-1")


@mock_mediaconnect
def test_delete_flow_succeeds():
    client = boto3.client("mediaconnect", region_name=region)
    channel_config = _create_flow_config("test-Flow-1")

    create_response = client.create_flow(**channel_config)
    create_response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    flow_arn = create_response["Flow"]["FlowArn"]
    delete_response = client.delete_flow(FlowArn=flow_arn)
    delete_response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    delete_response["FlowArn"].should.equal(flow_arn)
    delete_response["Status"].should.equal("STANDBY")


@mock_mediaconnect
def test_start_stop_flow_succeeds():
    client = boto3.client("mediaconnect", region_name=region)
    channel_config = _create_flow_config("test-Flow-1")

    create_response = client.create_flow(**channel_config)
    create_response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    create_response["Flow"]["Status"].should.equal("STANDBY")
    flow_arn = create_response["Flow"]["FlowArn"]

    start_response = client.start_flow(FlowArn=flow_arn)
    start_response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    start_response["FlowArn"].should.equal(flow_arn)
    start_response["Status"].should.equal("STARTING")

    describe_response = client.describe_flow(FlowArn=flow_arn)
    describe_response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    describe_response["Flow"]["Status"].should.equal("ACTIVE")

    stop_response = client.stop_flow(FlowArn=flow_arn)
    stop_response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    stop_response["FlowArn"].should.equal(flow_arn)
    stop_response["Status"].should.equal("STOPPING")

    describe_response = client.describe_flow(FlowArn=flow_arn)
    describe_response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    describe_response["Flow"]["Status"].should.equal("STANDBY")


@mock_mediaconnect
def test_tag_resource_succeeds():
    client = boto3.client("mediaconnect", region_name=region)

    tag_response = client.tag_resource(ResourceArn="some-arn", Tags={"Tag1": "Value1"})
    tag_response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    list_response = client.list_tags_for_resource(ResourceArn="some-arn")
    list_response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    list_response["Tags"].should.equal({"Tag1": "Value1"})


@mock_mediaconnect
def test_add_flow_vpc_interfaces_succeeds():
    client = boto3.client("mediaconnect", region_name=region)
    channel_config = _create_flow_config("test-Flow-1")

    create_response = client.create_flow(**channel_config)
    create_response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    create_response["Flow"]["Status"].should.equal("STANDBY")
    flow_arn = create_response["Flow"]["FlowArn"]

    client.add_flow_vpc_interfaces(
        FlowArn=flow_arn,
        VpcInterfaces=[
            {
                "Name": "VPCInterface",
                "SubnetId": "",
                "SecurityGroupIds": [],
                "RoleArn": "",
            }
        ],
    )

    describe_response = client.describe_flow(FlowArn=flow_arn)
    describe_response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    describe_response["Flow"]["VpcInterfaces"].should.equal(
        [
            {
                "Name": "VPCInterface",
                "RoleArn": "",
                "SecurityGroupIds": [],
                "SubnetId": "",
            }
        ]
    )


@mock_mediaconnect
def test_add_flow_vpc_interfaces_fails():
    client = boto3.client("mediaconnect", region_name=region)
    flow_arn = "unknown-flow"
    with pytest.raises(ClientError) as err:
        client.add_flow_vpc_interfaces(FlowArn=flow_arn, VpcInterfaces=[])
    err = err.value.response["Error"]
    err["Code"].should.equal("NotFoundException")
    err["Message"].should.equal("flow with arn=unknown-flow not found")


@mock_mediaconnect
def test_remove_flow_vpc_interface_succeeds():
    client = boto3.client("mediaconnect", region_name=region)
    channel_config = _create_flow_config("test-Flow-1")

    create_response = client.create_flow(**channel_config)
    create_response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    create_response["Flow"]["Status"].should.equal("STANDBY")
    flow_arn = create_response["Flow"]["FlowArn"]

    client.add_flow_vpc_interfaces(
        FlowArn=flow_arn,
        VpcInterfaces=[
            {
                "Name": "VPCInterface",
                "SubnetId": "",
                "SecurityGroupIds": [],
                "RoleArn": "",
            }
        ],
    )

    describe_response = client.describe_flow(FlowArn=flow_arn)
    describe_response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    len(describe_response["Flow"]["VpcInterfaces"]).should.equal(1)

    client.remove_flow_vpc_interface(FlowArn=flow_arn, VpcInterfaceName="VPCInterface")

    describe_response = client.describe_flow(FlowArn=flow_arn)
    len(describe_response["Flow"]["VpcInterfaces"]).should.equal(0)


@mock_mediaconnect
def test_remove_flow_vpc_interface_fails():
    client = boto3.client("mediaconnect", region_name=region)
    flow_arn = "unknown-flow"
    with pytest.raises(ClientError) as err:
        client.remove_flow_vpc_interface(
            FlowArn=flow_arn, VpcInterfaceName="VPCInterface"
        )
    err = err.value.response["Error"]
    err["Code"].should.equal("NotFoundException")
    err["Message"].should.equal("flow with arn=unknown-flow not found")


@mock_mediaconnect
def test_add_flow_outputs_succeeds():
    client = boto3.client("mediaconnect", region_name=region)
    channel_config = _create_flow_config("test-Flow-1")

    create_response = client.create_flow(**channel_config)
    create_response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    create_response["Flow"]["Status"].should.equal("STANDBY")
    flow_arn = create_response["Flow"]["FlowArn"]

    client.add_flow_outputs(
        FlowArn=flow_arn,
        Outputs=[
            {"Description": "string", "Name": "string", "Port": 123, "Protocol": "rist"}
        ],
    )

    describe_response = client.describe_flow(FlowArn=flow_arn)
    describe_response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    describe_response["Flow"]["Outputs"].should.equal(
        [{"Description": "string", "Name": "string", "Port": 123}]
    )


@mock_mediaconnect
def test_add_flow_outputs_fails():
    client = boto3.client("mediaconnect", region_name=region)
    flow_arn = "unknown-flow"
    with pytest.raises(ClientError) as err:
        client.add_flow_outputs(FlowArn=flow_arn, Outputs=[])
    err = err.value.response["Error"]
    err["Code"].should.equal("NotFoundException")
    err["Message"].should.equal("flow with arn=unknown-flow not found")


@mock_mediaconnect
def test_remove_flow_output_fails():
    client = boto3.client("mediaconnect", region_name=region)
    flow_arn = "unknown-flow"
    output_arn = "unknown-arn"
    with pytest.raises(ClientError) as err:
        client.remove_flow_output(FlowArn=flow_arn, OutputArn=output_arn)
    err = err.value.response["Error"]
    err["Code"].should.equal("NotFoundException")
    err["Message"].should.equal("flow with arn=unknown-flow not found")


@mock_mediaconnect
def test_remove_flow_output_succeeds():
    client = boto3.client("mediaconnect", region_name=region)
    channel_config = _create_flow_config("test-Flow-1")

    create_response = client.create_flow(**channel_config)
    create_response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    create_response["Flow"]["Status"].should.equal("STANDBY")
    flow_arn = create_response["Flow"]["FlowArn"]

    client.add_flow_outputs(
        FlowArn=flow_arn,
        Outputs=[
            {"Description": "string", "Name": "string", "Port": 123, "Protocol": "rist"}
        ],
    )

    describe_response = client.describe_flow(FlowArn=flow_arn)
    describe_response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    len(describe_response["Flow"]["Outputs"]).should.equal(1)

    client.remove_flow_output(FlowArn=flow_arn, OutputArn="string")

    describe_response = client.describe_flow(FlowArn=flow_arn)
    len(describe_response["Flow"]["Outputs"]).should.equal(0)
