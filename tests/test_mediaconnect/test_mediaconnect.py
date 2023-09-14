from uuid import UUID

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_mediaconnect
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

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
    assert _arn_list[:6] == ["arn", "aws", "mediaconnect", region, ACCOUNT_ID, type_]
    UUID(_arn_list[6])
    assert _arn_list[-1] == name


@mock_mediaconnect
def test_create_flow_succeeds():
    client = boto3.client("mediaconnect", region_name=region)
    channel_config = _create_flow_config("test-Flow-1")

    response = client.create_flow(**channel_config)

    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    _check_mediaconnect_arn(
        type_="flow", arn=response["Flow"]["FlowArn"], name="test-Flow-1"
    )
    assert response["Flow"]["Name"] == "test-Flow-1"
    assert response["Flow"]["Status"] == "STANDBY"
    assert response["Flow"]["Outputs"][0]["Name"] == "Output-1"
    assert response["Flow"]["Outputs"][1]["ListenerAddress"] == "1.0.0.0"
    assert response["Flow"]["Outputs"][2]["ListenerAddress"] == "2.0.0.0"
    assert response["Flow"]["Source"]["IngestIp"] == "127.0.0.0"
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

    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    _check_mediaconnect_arn(
        type_="flow", arn=response["Flow"]["FlowArn"], name="test-Flow-1"
    )
    assert response["Flow"]["Name"] == "test-Flow-1"
    assert response["Flow"]["Status"] == "STANDBY"
    assert response["Flow"]["Sources"][0]["IngestIp"] == "127.0.0.0"
    assert response["Flow"]["Sources"][1]["IngestIp"] == "127.0.0.1"
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
    assert len(response["Flows"]) == 2

    assert response["Flows"][0]["Name"] == "test-Flow-1"
    assert response["Flows"][0]["AvailabilityZone"] == "AZ1"
    assert response["Flows"][0]["SourceType"] == "OWNED"
    assert response["Flows"][0]["Status"] == "STANDBY"

    assert response["Flows"][1]["Name"] == "test-Flow-2"
    assert response["Flows"][1]["AvailabilityZone"] == "AZ1"
    assert response["Flows"][1]["SourceType"] == "OWNED"
    assert response["Flows"][1]["Status"] == "STANDBY"


@mock_mediaconnect
def test_describe_flow_succeeds():
    client = boto3.client("mediaconnect", region_name=region)
    channel_config = _create_flow_config("test-Flow-1")

    create_response = client.create_flow(**channel_config)
    assert create_response["ResponseMetadata"]["HTTPStatusCode"] == 200
    flow_arn = create_response["Flow"]["FlowArn"]
    describe_response = client.describe_flow(FlowArn=flow_arn)
    assert describe_response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert describe_response["Flow"]["Name"] == "test-Flow-1"


@mock_mediaconnect
def test_delete_flow_succeeds():
    client = boto3.client("mediaconnect", region_name=region)
    channel_config = _create_flow_config("test-Flow-1")

    create_response = client.create_flow(**channel_config)
    assert create_response["ResponseMetadata"]["HTTPStatusCode"] == 200
    flow_arn = create_response["Flow"]["FlowArn"]
    delete_response = client.delete_flow(FlowArn=flow_arn)
    assert delete_response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert delete_response["FlowArn"] == flow_arn
    assert delete_response["Status"] == "STANDBY"


@mock_mediaconnect
def test_start_stop_flow_succeeds():
    client = boto3.client("mediaconnect", region_name=region)
    channel_config = _create_flow_config("test-Flow-1")

    create_response = client.create_flow(**channel_config)
    assert create_response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert create_response["Flow"]["Status"] == "STANDBY"
    flow_arn = create_response["Flow"]["FlowArn"]

    start_response = client.start_flow(FlowArn=flow_arn)
    assert start_response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert start_response["FlowArn"] == flow_arn
    assert start_response["Status"] == "STARTING"

    describe_response = client.describe_flow(FlowArn=flow_arn)
    assert describe_response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert describe_response["Flow"]["Status"] == "ACTIVE"

    stop_response = client.stop_flow(FlowArn=flow_arn)
    assert stop_response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert stop_response["FlowArn"] == flow_arn
    assert stop_response["Status"] == "STOPPING"

    describe_response = client.describe_flow(FlowArn=flow_arn)
    assert describe_response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert describe_response["Flow"]["Status"] == "STANDBY"


@mock_mediaconnect
def test_unknown_flow():
    client = boto3.client("mediaconnect", region_name=region)

    with pytest.raises(ClientError) as exc:
        client.describe_flow(FlowArn="unknown")
    assert exc.value.response["Error"]["Code"] == "NotFoundException"

    with pytest.raises(ClientError) as exc:
        client.delete_flow(FlowArn="unknown")
    assert exc.value.response["Error"]["Code"] == "NotFoundException"

    with pytest.raises(ClientError) as exc:
        client.start_flow(FlowArn="unknown")
    assert exc.value.response["Error"]["Code"] == "NotFoundException"

    with pytest.raises(ClientError) as exc:
        client.stop_flow(FlowArn="unknown")
    assert exc.value.response["Error"]["Code"] == "NotFoundException"

    with pytest.raises(ClientError) as exc:
        client.list_tags_for_resource(ResourceArn="unknown")
    assert exc.value.response["Error"]["Code"] == "NotFoundException"


@mock_mediaconnect
def test_tag_resource_succeeds():
    client = boto3.client("mediaconnect", region_name=region)

    tag_response = client.tag_resource(ResourceArn="some-arn", Tags={"Tag1": "Value1"})
    assert tag_response["ResponseMetadata"]["HTTPStatusCode"] == 200

    list_response = client.list_tags_for_resource(ResourceArn="some-arn")
    assert list_response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert list_response["Tags"] == {"Tag1": "Value1"}


@mock_mediaconnect
def test_add_flow_vpc_interfaces_succeeds():
    client = boto3.client("mediaconnect", region_name=region)
    channel_config = _create_flow_config("test-Flow-1")

    create_response = client.create_flow(**channel_config)
    assert create_response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert create_response["Flow"]["Status"] == "STANDBY"
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
    assert describe_response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert describe_response["Flow"]["VpcInterfaces"] == [
        {
            "Name": "VPCInterface",
            "RoleArn": "",
            "SecurityGroupIds": [],
            "SubnetId": "",
        }
    ]


@mock_mediaconnect
def test_add_flow_vpc_interfaces_fails():
    client = boto3.client("mediaconnect", region_name=region)
    flow_arn = "unknown-flow"
    with pytest.raises(ClientError) as err:
        client.add_flow_vpc_interfaces(FlowArn=flow_arn, VpcInterfaces=[])
    err = err.value.response["Error"]
    assert err["Code"] == "NotFoundException"
    assert err["Message"] == "flow with arn=unknown-flow not found"


@mock_mediaconnect
def test_remove_flow_vpc_interface_succeeds():
    client = boto3.client("mediaconnect", region_name=region)
    channel_config = _create_flow_config("test-Flow-1")

    create_response = client.create_flow(**channel_config)
    assert create_response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert create_response["Flow"]["Status"] == "STANDBY"
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
    assert describe_response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert len(describe_response["Flow"]["VpcInterfaces"]) == 1

    client.remove_flow_vpc_interface(FlowArn=flow_arn, VpcInterfaceName="VPCInterface")

    describe_response = client.describe_flow(FlowArn=flow_arn)
    assert len(describe_response["Flow"]["VpcInterfaces"]) == 0


@mock_mediaconnect
def test_remove_flow_vpc_interface_fails():
    client = boto3.client("mediaconnect", region_name=region)
    flow_arn = "unknown-flow"
    with pytest.raises(ClientError) as err:
        client.remove_flow_vpc_interface(
            FlowArn=flow_arn, VpcInterfaceName="VPCInterface"
        )
    err = err.value.response["Error"]
    assert err["Code"] == "NotFoundException"
    assert err["Message"] == "flow with arn=unknown-flow not found"


@mock_mediaconnect
def test_add_flow_outputs_succeeds():
    client = boto3.client("mediaconnect", region_name=region)
    channel_config = _create_flow_config("test-Flow-1")

    create_response = client.create_flow(**channel_config)
    assert create_response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert create_response["Flow"]["Status"] == "STANDBY"
    flow_arn = create_response["Flow"]["FlowArn"]

    client.add_flow_outputs(
        FlowArn=flow_arn,
        Outputs=[
            {"Description": "string", "Name": "string", "Port": 123, "Protocol": "rist"}
        ],
    )

    response = client.describe_flow(FlowArn=flow_arn)
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    outputs = response["Flow"]["Outputs"]
    assert outputs == [{"Description": "string", "Name": "string", "Port": 123}]


@mock_mediaconnect
def test_add_flow_outputs_fails():
    client = boto3.client("mediaconnect", region_name=region)
    flow_arn = "unknown-flow"
    with pytest.raises(ClientError) as err:
        client.add_flow_outputs(FlowArn=flow_arn, Outputs=[])
    err = err.value.response["Error"]
    assert err["Code"] == "NotFoundException"
    assert err["Message"] == "flow with arn=unknown-flow not found"


@mock_mediaconnect
def test_update_flow_output_succeeds():
    client = boto3.client("mediaconnect", region_name=region)
    channel_config = _create_flow_config("test-Flow-1")

    create_response = client.create_flow(**channel_config)
    assert create_response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert create_response["Flow"]["Status"] == "STANDBY"
    flow_arn = create_response["Flow"]["FlowArn"]
    output_arn = create_response["Flow"]["Outputs"][0]["OutputArn"]

    update_response = client.update_flow_output(
        FlowArn=flow_arn, OutputArn=output_arn, Description="new description"
    )
    assert update_response["Output"]["Description"] == "new description"


@mock_mediaconnect
def test_update_flow_output_fails():
    client = boto3.client("mediaconnect", region_name=region)
    flow_arn = "unknown-flow"
    with pytest.raises(ClientError) as err:
        client.update_flow_output(
            FlowArn=flow_arn,
            OutputArn="some-arn",
            Description="new description",
        )
    err = err.value.response["Error"]
    assert err["Code"] == "NotFoundException"
    assert err["Message"] == "flow with arn=unknown-flow not found"


@mock_mediaconnect
def test_remove_flow_output_fails():
    client = boto3.client("mediaconnect", region_name=region)
    flow_arn = "unknown-flow"
    output_arn = "unknown-arn"
    with pytest.raises(ClientError) as err:
        client.remove_flow_output(FlowArn=flow_arn, OutputArn=output_arn)
    err = err.value.response["Error"]
    assert err["Code"] == "NotFoundException"
    assert err["Message"] == "flow with arn=unknown-flow not found"


@mock_mediaconnect
def test_remove_flow_output_succeeds():
    client = boto3.client("mediaconnect", region_name=region)
    channel_config = _create_flow_config("test-Flow-1")

    create_response = client.create_flow(**channel_config)
    assert create_response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert create_response["Flow"]["Status"] == "STANDBY"
    flow_arn = create_response["Flow"]["FlowArn"]

    client.add_flow_outputs(
        FlowArn=flow_arn,
        Outputs=[
            {"Description": "string", "Name": "string", "Port": 123, "Protocol": "rist"}
        ],
    )

    describe_response = client.describe_flow(FlowArn=flow_arn)
    assert describe_response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert len(describe_response["Flow"]["Outputs"]) == 1

    client.remove_flow_output(FlowArn=flow_arn, OutputArn="string")

    describe_response = client.describe_flow(FlowArn=flow_arn)
    assert len(describe_response["Flow"]["Outputs"]) == 0


@mock_mediaconnect
def test_add_flow_sources_fails():
    client = boto3.client("mediaconnect", region_name=region)
    flow_arn = "unknown-flow"
    with pytest.raises(ClientError) as err:
        client.add_flow_sources(FlowArn=flow_arn, Sources=[])
    err = err.value.response["Error"]
    assert err["Code"] == "NotFoundException"
    assert err["Message"] == "flow with arn=unknown-flow not found"


@mock_mediaconnect
def test_add_flow_sources_succeeds():
    client = boto3.client("mediaconnect", region_name=region)
    channel_config = _create_flow_config("test-Flow-1")

    create_response = client.create_flow(**channel_config)
    assert create_response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert create_response["Flow"]["Status"] == "STANDBY"
    flow_arn = create_response["Flow"]["FlowArn"]

    client.add_flow_sources(
        FlowArn=flow_arn,
        Sources=[
            {
                "Description": "string",
                "Name": "string",
                "Protocol": "rist",
                "SenderControlPort": 123,
            }
        ],
    )

    describe_response = client.describe_flow(FlowArn=flow_arn)
    assert describe_response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert len(describe_response["Flow"]["Sources"]) == 1


@mock_mediaconnect
def test_update_flow_source_fails():
    client = boto3.client("mediaconnect", region_name=region)
    flow_arn = "unknown-flow"
    source_arn = "unknown-source"

    channel_config = _create_flow_config("test-Flow-1")
    client.create_flow(**channel_config)

    with pytest.raises(ClientError) as err:
        client.update_flow_source(
            FlowArn=flow_arn, SourceArn=source_arn, Description="new description"
        )
    err = err.value.response["Error"]
    assert err["Code"] == "NotFoundException"
    assert err["Message"] == "flow with arn=unknown-flow not found"


@mock_mediaconnect
def test_update_flow_source_succeeds():
    client = boto3.client("mediaconnect", region_name=region)
    channel_config = _create_flow_config("test-Flow-1")

    create_response = client.create_flow(**channel_config)
    assert create_response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert create_response["Flow"]["Status"] == "STANDBY"
    flow_arn = create_response["Flow"]["FlowArn"]

    add_response = client.add_flow_sources(
        FlowArn=flow_arn,
        Sources=[
            {
                "Description": "string",
                "Name": "string",
                "Protocol": "rist",
                "SenderControlPort": 123,
            }
        ],
    )

    describe_response = client.describe_flow(FlowArn=flow_arn)
    assert describe_response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert len(describe_response["Flow"]["Sources"]) == 1

    source_arn = add_response["Sources"][0]["SourceArn"]

    update_response = client.update_flow_source(
        FlowArn=flow_arn, SourceArn=source_arn, Description="new description"
    )
    assert update_response["Source"]["Description"] == "new description"


@mock_mediaconnect
def test_grant_flow_entitlements_fails():
    client = boto3.client("mediaconnect", region_name=region)
    flow_arn = "unknown-flow"

    channel_config = _create_flow_config("test-Flow-1")
    client.create_flow(**channel_config)

    with pytest.raises(ClientError) as err:
        client.grant_flow_entitlements(
            FlowArn=flow_arn,
            Entitlements=[
                {
                    "DataTransferSubscriberFeePercent": 12,
                    "Description": "A new entitlement",
                    "Encryption": {"Algorithm": "aes256", "RoleArn": "some:role"},
                    "EntitlementStatus": "ENABLED",
                    "Name": "Entitlement-B",
                    "Subscribers": [],
                }
            ],
        )
    err = err.value.response["Error"]
    assert err["Code"] == "NotFoundException"
    assert err["Message"] == "flow with arn=unknown-flow not found"


@mock_mediaconnect
def test_grant_flow_entitlements_succeeds():
    client = boto3.client("mediaconnect", region_name=region)
    channel_config = _create_flow_config("test-Flow-1")

    create_response = client.create_flow(**channel_config)
    assert create_response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert create_response["Flow"]["Status"] == "STANDBY"
    flow_arn = create_response["Flow"]["FlowArn"]

    describe_response = client.describe_flow(FlowArn=flow_arn)
    assert describe_response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert len(describe_response["Flow"]["Sources"]) == 1

    grant_response = client.grant_flow_entitlements(
        FlowArn=flow_arn,
        Entitlements=[
            {
                "DataTransferSubscriberFeePercent": 12,
                "Description": "A new entitlement",
                "Encryption": {"Algorithm": "aes256", "RoleArn": "some:role"},
                "EntitlementStatus": "ENABLED",
                "Name": "Entitlement-B",
                "Subscribers": [],
            },
            {
                "DataTransferSubscriberFeePercent": 12,
                "Description": "Another new entitlement",
                "Encryption": {"Algorithm": "aes256", "RoleArn": "some:role"},
                "EntitlementStatus": "ENABLED",
                "Name": "Entitlement-C",
                "Subscribers": [],
            },
        ],
    )

    entitlements = grant_response["Entitlements"]
    assert len(entitlements) == 2
    entitlement_names = [entitlement["Name"] for entitlement in entitlements]
    assert "Entitlement-B" in entitlement_names
    assert "Entitlement-C" in entitlement_names


@mock_mediaconnect
def test_revoke_flow_entitlement_fails():
    client = boto3.client("mediaconnect", region_name=region)
    channel_config = _create_flow_config("test-Flow-1")

    create_response = client.create_flow(**channel_config)
    assert create_response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert create_response["Flow"]["Status"] == "STANDBY"
    flow_arn = create_response["Flow"]["FlowArn"]

    describe_response = client.describe_flow(FlowArn=flow_arn)
    assert describe_response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert len(describe_response["Flow"]["Entitlements"]) == 1

    with pytest.raises(ClientError) as err:
        client.revoke_flow_entitlement(
            FlowArn=flow_arn, EntitlementArn="some-other-arn"
        )
    err = err.value.response["Error"]
    assert err["Code"] == "NotFoundException"
    assert err["Message"] == "entitlement with arn=some-other-arn not found"


@mock_mediaconnect
def test_revoke_flow_entitlement_succeeds():
    client = boto3.client("mediaconnect", region_name=region)
    channel_config = _create_flow_config("test-Flow-1")

    create_response = client.create_flow(**channel_config)
    assert create_response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert create_response["Flow"]["Status"] == "STANDBY"
    flow_arn = create_response["Flow"]["FlowArn"]

    describe_response = client.describe_flow(FlowArn=flow_arn)
    assert describe_response["ResponseMetadata"]["HTTPStatusCode"] == 200
    entitlement_arn = describe_response["Flow"]["Entitlements"][0]["EntitlementArn"]

    revoke_response = client.revoke_flow_entitlement(
        FlowArn=flow_arn, EntitlementArn=entitlement_arn
    )
    assert revoke_response["FlowArn"] == flow_arn
    assert revoke_response["EntitlementArn"] == entitlement_arn

    describe_response = client.describe_flow(FlowArn=flow_arn)
    assert describe_response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert len(describe_response["Flow"]["Entitlements"]) == 0


@mock_mediaconnect
def test_update_flow_entitlement_fails():
    client = boto3.client("mediaconnect", region_name=region)
    channel_config = _create_flow_config("test-Flow-1")

    create_response = client.create_flow(**channel_config)
    assert create_response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert create_response["Flow"]["Status"] == "STANDBY"
    flow_arn = create_response["Flow"]["FlowArn"]

    describe_response = client.describe_flow(FlowArn=flow_arn)
    assert describe_response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert len(describe_response["Flow"]["Entitlements"]) == 1

    with pytest.raises(ClientError) as err:
        client.update_flow_entitlement(
            FlowArn=flow_arn,
            EntitlementArn="some-other-arn",
            Description="new description",
        )
    err = err.value.response["Error"]
    assert err["Code"] == "NotFoundException"
    assert err["Message"] == "entitlement with arn=some-other-arn not found"


@mock_mediaconnect
def test_update_flow_entitlement_succeeds():
    client = boto3.client("mediaconnect", region_name=region)
    channel_config = _create_flow_config("test-Flow-1")

    create_response = client.create_flow(**channel_config)
    assert create_response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert create_response["Flow"]["Status"] == "STANDBY"
    flow_arn = create_response["Flow"]["FlowArn"]

    describe_response = client.describe_flow(FlowArn=flow_arn)
    assert describe_response["ResponseMetadata"]["HTTPStatusCode"] == 200
    entitlement_arn = describe_response["Flow"]["Entitlements"][0]["EntitlementArn"]

    update_response = client.update_flow_entitlement(
        FlowArn=flow_arn,
        EntitlementArn=entitlement_arn,
        Description="new description",
    )
    assert update_response["FlowArn"] == flow_arn
    entitlement = update_response["Entitlement"]
    assert entitlement["EntitlementArn"] == entitlement_arn
    assert entitlement["Description"] == "new description"
