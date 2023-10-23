import boto3

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
        resp["Arn"]
        == "arn:aws:sagemaker:eu-west-1:123456789012:device/test-device-name"
    )
    assert resp["DeviceId"] == "device-1"
    assert resp["IotThingName"] == "test-device-name"
    assert resp["Status"] == "SUCCEEDED"
