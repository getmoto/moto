from datetime import datetime
from typing import List
from unittest import SkipTest

import boto3
import pytest
from botocore.exceptions import ClientError
from dateutil.tz import tzutc
from freezegun import freeze_time

from moto import mock_aws, settings
from moto.moto_api import state_manager


@mock_aws
def test_provision_device() -> None:
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Can't use ManagedState in ServerMode")
    client = boto3.client("panorama", region_name="eu-west-1")
    given_device_name = "test-device-name"
    state_manager.set_transition(
        model_name=f"panorama::device_{given_device_name}_provisioning_status",
        transition={"progression": "manual", "times": 1},
    )
    resp = client.provision_device(
        Description=given_device_name,
        Name="test-device-name",
        NetworkingConfiguration={
            "Ethernet0": {
                "ConnectionType": "STATIC_IP",
                "StaticIpConnectionInfo": {
                    "DefaultGateway": "192.168.1.1",
                    "Dns": [
                        "8.8.8.8",
                    ],
                    "IpAddress": "192.168.1.10",
                    "Mask": "255.255.255.0",
                },
            },
            "Ethernet1": {
                "ConnectionType": "dhcp",
            },
            "Ntp": {
                "NtpServers": [
                    "0.pool.ntp.org",
                    "1.pool.ntp.org",
                    "0.fr.pool.ntp.org",
                ]
            },
        },
        Tags={"Key": "test-key", "Value": "test-value"},
    )
    assert (
        resp["Arn"] == "arn:aws:panorama:eu-west-1:123456789012:device/test-device-name"
    )
    assert resp["Certificates"] == b"certificate"
    assert resp["DeviceId"] == "device-RsozEWjZpeNe3SXHidX3mg=="
    assert resp["IotThingName"] == ""
    assert resp["Status"] == "AWAITING_PROVISIONING"


@mock_aws
def test_describe_device() -> None:
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Can't freeze time in ServerMode")
    client = boto3.client("panorama", region_name="eu-west-1")
    given_device_name = "test-device-name"
    state_manager.set_transition(
        model_name=f"panorama::device_{given_device_name}_provisioning_status",
        transition={"progression": "immediate"},
    )
    with freeze_time("2020-01-01 12:00:00"):
        resp = client.provision_device(
            Description="test device description",
            Name=given_device_name,
            NetworkingConfiguration={
                "Ethernet0": {
                    "ConnectionType": "STATIC_IP",
                    "StaticIpConnectionInfo": {
                        "DefaultGateway": "192.168.1.1",
                        "Dns": [
                            "8.8.8.8",
                        ],
                        "IpAddress": "192.168.1.10",
                        "Mask": "255.255.255.0",
                    },
                },
                "Ethernet1": {
                    "ConnectionType": "dhcp",
                },
                "Ntp": {
                    "NtpServers": [
                        "0.pool.ntp.org",
                        "1.pool.ntp.org",
                        "0.fr.pool.ntp.org",
                    ]
                },
            },
            Tags={"Key": "test-key", "Value": "test-value"},
        )

    resp = client.describe_device(DeviceId=resp["DeviceId"])

    assert resp["AlternateSoftwares"] == [{"Version": "0.2.1"}]
    assert (
        resp["Arn"] == "arn:aws:panorama:eu-west-1:123456789012:device/test-device-name"
    )
    assert resp["Brand"] == "AWS_PANORAMA"
    assert resp["CreatedTime"] == datetime(2020, 1, 1, 12, 0, tzinfo=tzutc())
    assert resp["CurrentNetworkingStatus"] == {
        "Ethernet0Status": {
            "ConnectionStatus": "CONNECTED",
            "HwAddress": "8C:0F:5F:60:F5:C4",
            "IpAddress": "192.168.1.300/24",
        },
        "Ethernet1Status": {
            "ConnectionStatus": "NOT_CONNECTED",
            "HwAddress": "8C:0F:6F:60:F4:F1",
            "IpAddress": "--",
        },
        "LastUpdatedTime": datetime(2020, 1, 1, 12, 0, tzinfo=tzutc()),
        "NtpStatus": {
            "ConnectionStatus": "CONNECTED",
            "IpAddress": "91.224.149.41:123",
            "NtpServerName": "0.pool.ntp.org",
        },
    }
    assert resp["CurrentSoftware"] == "6.2.1"
    assert resp["Description"] == "test device description"
    assert resp["DeviceAggregatedStatus"] == "ONLINE"
    assert resp["DeviceConnectionStatus"] == "ONLINE"
    assert resp["DeviceId"] == "device-RsozEWjZpeNe3SXHidX3mg=="
    assert resp["LatestDeviceJob"] == {"JobType": "REBOOT", "Status": "COMPLETED"}
    assert resp["LatestSoftware"] == "6.2.1"
    assert resp["LeaseExpirationTime"] == datetime(2020, 1, 6, 12, 0, tzinfo=tzutc())
    assert resp["Name"] == "test-device-name"
    assert resp["ProvisioningStatus"] == "SUCCEEDED"
    assert resp["SerialNumber"] == "GAD81E29013274749"
    assert resp["Tags"] == {"Key": "test-key", "Value": "test-value"}
    assert resp["Type"] == "PANORAMA_APPLIANCE"


@mock_aws
def test_provision_device_aggregated_status_lifecycle() -> None:
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Can't use ManagedState in ServerMode")
    client = boto3.client("panorama", region_name="eu-west-1")
    given_device_name = "test-device-name"
    state_manager.set_transition(
        model_name=f"panorama::device_{given_device_name}_aggregated_status",
        transition={"progression": "manual", "times": 1},
    )
    state_manager.set_transition(
        model_name=f"panorama::device_{given_device_name}_provisioning_status",
        transition={"progression": "manual", "times": 2},
    )
    device_id = client.provision_device(
        Description="test device description",
        Name=given_device_name,
        NetworkingConfiguration={
            "Ethernet0": {
                "ConnectionType": "STATIC_IP",
                "StaticIpConnectionInfo": {
                    "DefaultGateway": "192.168.1.1",
                    "Dns": [
                        "8.8.8.8",
                    ],
                    "IpAddress": "192.168.1.10",
                    "Mask": "255.255.255.0",
                },
            },
            "Ethernet1": {
                "ConnectionType": "dhcp",
            },
            "Ntp": {
                "NtpServers": [
                    "0.pool.ntp.org",
                    "1.pool.ntp.org",
                    "0.fr.pool.ntp.org",
                ]
            },
        },
        Tags={"Key": "test-key", "Value": "test-value"},
    )["DeviceId"]

    resp_1 = client.describe_device(DeviceId=device_id)
    assert (
        resp_1["Arn"]
        == "arn:aws:panorama:eu-west-1:123456789012:device/test-device-name"
    )
    assert resp_1["DeviceAggregatedStatus"] == "AWAITING_PROVISIONING"
    assert resp_1["ProvisioningStatus"] == "AWAITING_PROVISIONING"

    resp_2 = client.describe_device(DeviceId=device_id)
    assert (
        resp_2["Arn"]
        == "arn:aws:panorama:eu-west-1:123456789012:device/test-device-name"
    )
    assert resp_2["DeviceAggregatedStatus"] == "PENDING"
    assert resp_2["ProvisioningStatus"] == "AWAITING_PROVISIONING"

    resp_3 = client.describe_device(DeviceId=device_id)
    assert (
        resp_3["Arn"]
        == "arn:aws:panorama:eu-west-1:123456789012:device/test-device-name"
    )
    assert resp_3["DeviceAggregatedStatus"] == "ONLINE"
    assert resp_3["ProvisioningStatus"] == "PENDING"


@mock_aws
def test_list_device() -> None:
    client = boto3.client("panorama", region_name="eu-west-1")
    resp_1 = client.provision_device(
        Description="test device description 1",
        Name="test-device-name-1",
        Tags={"Key": "test-key", "Value": "test-value"},
    )
    resp_2 = client.provision_device(
        Description="test device description 2",
        Name="test-device-name-2",
        Tags={"Key": "test-key", "Value": "test-value"},
    )

    resp = client.list_devices()

    assert len(resp["Devices"]) == 2
    assert "Brand" in resp["Devices"][0]
    assert "CreatedTime" in resp["Devices"][0]
    assert "CurrentSoftware" in resp["Devices"][0]
    assert "Description" in resp["Devices"][0]
    assert "DeviceAggregatedStatus" in resp["Devices"][0]
    assert "DeviceId" in resp["Devices"][0]
    assert "LastUpdatedTime" in resp["Devices"][0]
    assert "LatestDeviceJob" in resp["Devices"][0]
    assert "LeaseExpirationTime" in resp["Devices"][0]
    assert "Name" in resp["Devices"][0]
    assert "ProvisioningStatus" in resp["Devices"][0]
    assert "Tags" in resp["Devices"][0]
    assert "Type" in resp["Devices"][0]
    assert resp["Devices"][0]["DeviceId"] == resp_1["DeviceId"]

    assert "Brand" in resp["Devices"][1]
    assert "CreatedTime" in resp["Devices"][1]
    assert "CurrentSoftware" in resp["Devices"][1]
    assert "Description" in resp["Devices"][1]
    assert "DeviceAggregatedStatus" in resp["Devices"][1]
    assert "DeviceId" in resp["Devices"][1]
    assert "LastUpdatedTime" in resp["Devices"][1]
    assert "LatestDeviceJob" in resp["Devices"][1]
    assert "LeaseExpirationTime" in resp["Devices"][1]
    assert "Name" in resp["Devices"][1]
    assert "ProvisioningStatus" in resp["Devices"][1]
    assert "Tags" in resp["Devices"][1]
    assert "Type" in resp["Devices"][1]
    assert resp["Devices"][1]["DeviceId"] == resp_2["DeviceId"]


@mock_aws
def test_list_device_name_filter() -> None:
    client = boto3.client("panorama", region_name="eu-west-1")
    resp_1 = client.provision_device(
        Description="test device description 1",
        Name="test-device-name-1",
        Tags={"Key": "test-key", "Value": "test-value"},
    )
    resp_2 = client.provision_device(
        Description="test device description 2",
        Name="test-device-name-2",
        Tags={"Key": "test-key", "Value": "test-value"},
    )
    _ = client.provision_device(
        Description="test device description 3",
        Name="another-test-device-name",
        Tags={"Key": "test-key", "Value": "test-value"},
    )

    resp = client.list_devices(NameFilter="test-")

    assert len(resp["Devices"]) == 2
    assert resp["Devices"][0]["DeviceId"] == resp_1["DeviceId"]
    assert resp["Devices"][1]["DeviceId"] == resp_2["DeviceId"]


@mock_aws
def test_list_device_max_result_and_next_token() -> None:
    client = boto3.client("panorama", region_name="eu-west-1")
    _ = client.provision_device(
        Description="test device description 1",
        Name="test-device-name-1",
        Tags={"Key": "test-key", "Value": "test-value"},
    )
    _ = client.provision_device(
        Description="test device description 2",
        Name="test-device-name-2",
        Tags={"Key": "test-key", "Value": "test-value"},
    )

    resp = client.list_devices(MaxResults=1)

    assert len(resp["Devices"]) == 1
    assert "NextToken" in resp

    resp = client.list_devices(MaxResults=1, NextToken=resp["NextToken"])

    assert len(resp["Devices"]) == 1
    assert "NextToken" not in resp


@pytest.mark.parametrize(
    "sort_order, indexes",
    [
        ("ASCENDING", [0, 1]),
        ("DESCENDING", [1, 0]),
    ],
)
@mock_aws
def test_list_devices_sort_order(sort_order: str, indexes: List[int]) -> None:
    client = boto3.client("panorama", region_name="eu-west-1")
    resp_1 = client.provision_device(
        Description="test device description 1",
        Name="test-device-name-1",
        Tags={"Key": "test-key", "Value": "test-value"},
    )
    resp_2 = client.provision_device(
        Description="test device description 2",
        Name="test-device-name-2",
        Tags={"Key": "test-key", "Value": "test-value"},
    )

    resp = client.list_devices(SortOrder=sort_order)

    assert len(resp["Devices"]) == 2
    assert resp["Devices"][indexes[0]]["DeviceId"] == resp_1["DeviceId"]
    assert resp["Devices"][indexes[1]]["DeviceId"] == resp_2["DeviceId"]


@pytest.mark.parametrize(
    "sort_by, indexes",
    [
        ("DEVICE_ID", [0, 1]),
        ("CREATED_TIME", [1, 0]),
        ("NAME", [0, 1]),
        ("DEVICE_AGGREGATED_STATUS", [1, 0]),
    ],
)
@mock_aws
def test_list_devices_sort_by(sort_by: str, indexes: List[int]) -> None:
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Can't freeze time in ServerMode")
    client = boto3.client("panorama", region_name="eu-west-1")
    state_manager.set_transition(
        model_name="panorama::device_test-device-name-2_aggregated_status",
        transition={"progression": "manual", "times": 1},
    )
    with freeze_time("2021-01-01 12:00:00"):
        resp_1 = client.provision_device(
            Description="test device description 1",
            Name="test-device-name-1",
            Tags={"Key": "test-key", "Value": "test-value"},
        )
    with freeze_time("2021-01-01 10:00:00"):
        resp_2 = client.provision_device(
            Description="test device description 2",
            Name="test-device-name-2",
            Tags={"Key": "test-key", "Value": "test-value"},
        )

    resp = client.list_devices(SortBy=sort_by)

    assert len(resp["Devices"]) == 2
    assert resp["Devices"][indexes[0]]["DeviceId"] == resp_1["DeviceId"]
    assert resp["Devices"][indexes[1]]["DeviceId"] == resp_2["DeviceId"]


@mock_aws
def test_list_devices_device_aggregated_status_filter() -> None:
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Can't use ManagedState in ServerMode")
    client = boto3.client("panorama", region_name="eu-west-1")
    state_manager.set_transition(
        model_name="panorama::device_test-device-name-2_aggregated_status",
        transition={"progression": "manual", "times": 1},
    )
    _ = client.provision_device(
        Description="test device description 1",
        Name="test-device-name-1",
        Tags={"Key": "test-key", "Value": "test-value"},
    )
    resp_2 = client.provision_device(
        Description="test device description 2",
        Name="test-device-name-2",
        Tags={"Key": "test-key", "Value": "test-value"},
    )
    # Need two advance to go from not-a-status to Pending
    client.describe_device(DeviceId=resp_2["DeviceId"])

    resp = client.list_devices(DeviceAggregatedStatusFilter="PENDING")

    assert len(resp["Devices"]) == 1
    assert resp["Devices"][0]["DeviceId"] == resp_2["DeviceId"]


@mock_aws
def test_update_device_metadata() -> None:
    client = boto3.client("panorama", region_name="eu-west-1")
    resp = client.provision_device(
        Description="test device description", Name="test-device-name"
    )

    client.update_device_metadata(
        DeviceId=resp["DeviceId"],
        Description="updated device description",
    )

    resp_updated = client.describe_device(DeviceId=resp["DeviceId"])

    assert resp_updated["Description"] == "updated device description"


@mock_aws
def test_delete_device() -> None:
    client = boto3.client("panorama", region_name="eu-west-1")
    resp = client.provision_device(
        Description="test device description", Name="test-device-name"
    )

    client.delete_device(DeviceId=resp["DeviceId"])

    with pytest.raises(ClientError) as ex:
        client.describe_device(DeviceId=resp["DeviceId"])
    err = ex.value.response
    assert err["Error"]["Code"] == "ValidationException"
    assert f"Device {resp['DeviceId']} not found" in err["Error"]["Message"]
    assert err["ResponseMetadata"]["HTTPStatusCode"] == 400
