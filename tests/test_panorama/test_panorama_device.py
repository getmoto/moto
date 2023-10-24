from datetime import datetime
from dateutil.tz import tzutc

import boto3
from freezegun import freeze_time

from moto import mock_panorama


@mock_panorama
def test_provision_device() -> None:
    client = boto3.client("panorama", region_name="eu-west-1")
    resp = client.provision_device(
        Description="test device description",
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


@mock_panorama
def test_describe_device() -> None:
    client = boto3.client("panorama", region_name="eu-west-1")
    with freeze_time("2020-01-01 12:00:00"):
        resp = client.provision_device(
            Description="test device description",
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
    assert resp["SerialNumber"] == "GAD81E29013274749"
    assert resp["Tags"] == {"Key": "test-key", "Value": "test-value"}
    assert resp["Type"] == "PANORAMA_APPLIANCE"
