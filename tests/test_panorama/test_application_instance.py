import datetime
from unittest import SkipTest
from unittest.mock import ANY

import boto3
from dateutil.tz import tzutc
from freezegun import freeze_time

from moto import mock_aws, settings

GIVEN_DEVICE_NAME = "not-a-device-name"
PROVISION_DEVICE_PARAMS = {
    "Description": "not a device description",
    "Name": GIVEN_DEVICE_NAME,
    "NetworkingConfiguration": {
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
    "Tags": {"Key": "test-key", "Value": "test-value"},
}


@mock_aws
def test_create_application_instance() -> None:
    # Given
    panorama_client = boto3.client("panorama", "eu-west-1")
    response_device_creation = panorama_client.provision_device(
        **PROVISION_DEVICE_PARAMS
    )

    # When
    response = panorama_client.create_application_instance(
        DefaultRuntimeContextDevice=response_device_creation["DeviceId"],
        Description="not a description",
        ManifestOverridesPayload={
            "PayloadData": "dumped_payload_data",
        },
        ManifestPayload={
            "PayloadData": "dumped_manifest_payload_data",
        },
        Name="not-a-name",
        RuntimeRoleArn="not-an-arn",
        Tags={
            "Key": "value",
        },
    )
    # Then
    assert isinstance(response["ApplicationInstanceId"], str)
    assert response["ApplicationInstanceId"].startswith("applicationInstance-")
    assert len(response["ApplicationInstanceId"]) == 42


@mock_aws
def test_describe_application_instance() -> None:
    # Given
    panorama_client = boto3.client("panorama", "eu-west-1")
    response_device_creation = panorama_client.provision_device(
        **PROVISION_DEVICE_PARAMS
    )
    given_application_instance_name = "not-a-name"
    given_application_instance_arn = "not-an-arn"
    response_created = panorama_client.create_application_instance(
        DefaultRuntimeContextDevice=response_device_creation["DeviceId"],
        Description="not a description",
        ManifestOverridesPayload={
            "PayloadData": "dumped_payload_data",
        },
        ManifestPayload={
            "PayloadData": "dumped_manifest_payload_data",
        },
        Name=given_application_instance_name,
        RuntimeRoleArn=given_application_instance_arn,
        Tags={
            "Key": "value",
        },
    )

    # When
    response = panorama_client.describe_application_instance(
        ApplicationInstanceId=response_created["ApplicationInstanceId"]
    )

    # Then
    assert (
        response["ApplicationInstanceId"] == response_created["ApplicationInstanceId"]
    )
    assert response.get("ApplicationInstanceIdToReplace") is None
    assert response["Arn"].startswith(
        "arn:aws:panorama:eu-west-1:123456789012:application-instance/"
    )
    assert response["Arn"].endswith(response_created["ApplicationInstanceId"])
    assert isinstance(response["CreatedTime"], datetime.datetime)
    assert (
        response["DefaultRuntimeContextDevice"] == response_device_creation["DeviceId"]
    )
    assert response["DefaultRuntimeContextDeviceName"] == "not-a-device-name"
    assert response["Description"] == "not a description"
    assert response["HealthStatus"] == "RUNNING"
    assert isinstance(response["LastUpdatedTime"], datetime.datetime)
    assert response["Name"] == given_application_instance_name
    assert response["RuntimeRoleArn"] == given_application_instance_arn
    assert response["Status"] == "DEPLOYMENT_SUCCEEDED"


@mock_aws
def test_create_application_instance_should_set_created_time() -> None:
    # Given
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Can't use ManagedState in ServerMode")
    panorama_client = boto3.client("panorama", "eu-west-1")
    response_device_creation = panorama_client.provision_device(
        **PROVISION_DEVICE_PARAMS
    )
    given_application_instance_name = "not-a-name"
    given_application_instance_arn = "not-an-arn"
    with freeze_time("2020-01-01 12:00:00"):
        response_created = panorama_client.create_application_instance(
            DefaultRuntimeContextDevice=response_device_creation["DeviceId"],
            Description="not a description",
            ManifestOverridesPayload={
                "PayloadData": "dumped_payload_data",
            },
            ManifestPayload={
                "PayloadData": "dumped_manifest_payload_data",
            },
            Name=given_application_instance_name,
            RuntimeRoleArn=given_application_instance_arn,
            Tags={
                "Key": "value",
            },
        )

    # When
    response = panorama_client.describe_application_instance(
        ApplicationInstanceId=response_created["ApplicationInstanceId"]
    )

    # Then
    assert response["CreatedTime"] == datetime.datetime(
        2020, 1, 1, 12, 0, 0, tzinfo=tzutc()
    )
    assert response["LastUpdatedTime"] == datetime.datetime(
        2020, 1, 1, 12, 0, 0, tzinfo=tzutc()
    )


@mock_aws
def test_describe_application_instance_details() -> None:
    # Given
    panorama_client = boto3.client("panorama", "eu-west-1")
    given_application_instance_name = "not-a-name"
    given_application_instance_arn = "not-an-arn"
    response_device_creation = panorama_client.provision_device(
        **PROVISION_DEVICE_PARAMS
    )
    given_manifest_payload = {
        "PayloadData": "dumped_manifest_payload_data",
    }
    given_manifest_overrides_payload = {
        "PayloadData": "dumped_payload_data",
    }
    response_created = panorama_client.create_application_instance(
        DefaultRuntimeContextDevice=response_device_creation["DeviceId"],
        Description="not a description",
        ManifestOverridesPayload=given_manifest_overrides_payload,
        ManifestPayload=given_manifest_payload,
        Name=given_application_instance_name,
        RuntimeRoleArn=given_application_instance_arn,
        Tags={
            "Key": "value",
        },
    )

    # When
    response = panorama_client.describe_application_instance_details(
        ApplicationInstanceId=response_created["ApplicationInstanceId"]
    )

    # Then
    assert (
        response["ApplicationInstanceId"] == response_created["ApplicationInstanceId"]
    )
    assert response.get("ApplicationInstanceIdToReplace") is None
    assert isinstance(response["CreatedTime"], datetime.datetime)
    assert (
        response["DefaultRuntimeContextDevice"] == response_device_creation["DeviceId"]
    )
    assert response["Description"] == "not a description"
    assert response["Name"] == given_application_instance_name
    assert response["ManifestPayload"] == given_manifest_payload
    assert response["ManifestOverridesPayload"] == given_manifest_overrides_payload


@mock_aws
def test_list_application_instances() -> None:
    # Given
    panorama_client = boto3.client("panorama", "eu-west-1")
    given_application_instance_name = "not-a-name"
    given_application_instance_arn = "not-an-arn"
    given_device_name = "not-a-device-name"
    response_device_creation = panorama_client.provision_device(
        **PROVISION_DEVICE_PARAMS
    )
    response_created_1 = panorama_client.create_application_instance(
        DefaultRuntimeContextDevice=response_device_creation["DeviceId"],
        Description="not a description",
        ManifestOverridesPayload={
            "PayloadData": "dumped_payload_data",
        },
        ManifestPayload={
            "PayloadData": "dumped_manifest_payload_data",
        },
        Name=given_application_instance_name,
        RuntimeRoleArn=given_application_instance_arn,
        Tags={
            "Key": "value",
        },
    )
    response_created_2 = panorama_client.create_application_instance(
        ApplicationInstanceIdToReplace=response_created_1["ApplicationInstanceId"],
        DefaultRuntimeContextDevice=response_device_creation["DeviceId"],
        Description="not a description",
        ManifestOverridesPayload={
            "PayloadData": "dumped_payload_data",
        },
        ManifestPayload={
            "PayloadData": "dumped_manifest_payload_data",
        },
        Name=given_application_instance_name,
        RuntimeRoleArn=given_application_instance_arn,
        Tags={
            "Key": "value",
        },
    )

    # When
    response_1 = panorama_client.list_application_instances(
        DeviceId=response_device_creation["DeviceId"],
        MaxResults=1,
    )
    response_2 = panorama_client.list_application_instances(
        DeviceId=response_device_creation["DeviceId"],
        MaxResults=1,
        NextToken=response_1["NextToken"],
    )

    # Then
    assert len(response_1["ApplicationInstances"]) == 1
    assert (
        response_1["ApplicationInstances"][0]["ApplicationInstanceId"]
        == response_created_1["ApplicationInstanceId"]
    )
    assert response_1["ApplicationInstances"][0]["Arn"].startswith(
        "arn:aws:panorama:eu-west-1:123456789012:application-instance/"
    )
    assert response_1["ApplicationInstances"][0]["Arn"].endswith(
        response_created_1["ApplicationInstanceId"]
    )
    assert isinstance(
        response_1["ApplicationInstances"][0]["CreatedTime"], datetime.datetime
    )
    assert (
        response_1["ApplicationInstances"][0]["DefaultRuntimeContextDevice"]
        == response_device_creation["DeviceId"]
    )
    assert (
        response_1["ApplicationInstances"][0]["DefaultRuntimeContextDeviceName"]
        == given_device_name
    )
    assert response_1["ApplicationInstances"][0]["Description"] == "not a description"
    assert response_1["ApplicationInstances"][0]["HealthStatus"] == "RUNNING"
    assert response_1["ApplicationInstances"][0]["Name"], response_created_1["Name"]
    assert response_1["ApplicationInstances"][0]["RuntimeContextStates"] == [
        {
            "DesiredState": "RUNNING",
            "DeviceReportedStatus": "RUNNING",
            "DeviceReportedTime": ANY,
            "RuntimeContextName": "string",
        },
        {
            "DesiredState": "REMOVED",
            "DeviceReportedStatus": "REMOVAL_IN_PROGRESS",
            "DeviceReportedTime": ANY,
            "RuntimeContextName": "string",
        },
    ]
    assert response_1["ApplicationInstances"][0]["Status"] == "REMOVAL_SUCCEEDED"
    assert response_1["ApplicationInstances"][0]["StatusDescription"] == "string"
    assert response_1["ApplicationInstances"][0]["Tags"] == {"Key": "value"}
    assert response_1["NextToken"] is not None

    assert len(response_2["ApplicationInstances"]) == 1
    assert (
        response_2["ApplicationInstances"][0]["ApplicationInstanceId"]
        == response_created_2["ApplicationInstanceId"]
    )
    assert "NextToken" not in response_2
    assert response_2["ApplicationInstances"][0]["RuntimeContextStates"] == [
        {
            "DesiredState": "RUNNING",
            "DeviceReportedStatus": "RUNNING",
            "DeviceReportedTime": ANY,
            "RuntimeContextName": "string",
        }
    ]


@mock_aws
def test_list_application_should_return_only_filtered_results_if_status_filter_used() -> (
    None
):
    # Given
    panorama_client = boto3.client("panorama", "eu-west-1")
    given_application_instance_name = "not-a-name"
    given_application_instance_name_2 = "not-a-name-2"
    given_application_instance_arn = "not-an-arn"
    response_device_creation = panorama_client.provision_device(
        **PROVISION_DEVICE_PARAMS
    )
    response_created_1 = panorama_client.create_application_instance(
        DefaultRuntimeContextDevice=response_device_creation["DeviceId"],
        Description="not a description",
        ManifestOverridesPayload={
            "PayloadData": "dumped_payload_data",
        },
        ManifestPayload={
            "PayloadData": "dumped_manifest_payload_data",
        },
        Name=given_application_instance_name,
        RuntimeRoleArn=given_application_instance_arn,
        Tags={
            "Key": "value",
        },
    )
    response_created_2 = panorama_client.create_application_instance(
        ApplicationInstanceIdToReplace=response_created_1["ApplicationInstanceId"],
        DefaultRuntimeContextDevice=response_device_creation["DeviceId"],
        Description="not a description",
        ManifestOverridesPayload={
            "PayloadData": "dumped_payload_data",
        },
        ManifestPayload={
            "PayloadData": "dumped_manifest_payload_data",
        },
        Name=given_application_instance_name_2,
        RuntimeRoleArn=given_application_instance_arn,
        Tags={
            "Key": "value",
        },
    )

    # When
    response_deployed = panorama_client.list_application_instances(
        DeviceId=response_device_creation["DeviceId"],
        MaxResults=123,
        StatusFilter="DEPLOYMENT_SUCCEEDED",
    )

    response_removed = panorama_client.list_application_instances(
        DeviceId=response_device_creation["DeviceId"],
        MaxResults=123,
        StatusFilter="REMOVAL_SUCCEEDED",
    )

    # Then
    assert len(response_removed["ApplicationInstances"]) == 1
    assert (
        response_removed["ApplicationInstances"][0]["ApplicationInstanceId"]
        == response_created_1["ApplicationInstanceId"]
    )
    assert len(response_deployed["ApplicationInstances"]) == 1
    assert (
        response_deployed["ApplicationInstances"][0]["ApplicationInstanceId"]
        == response_created_2["ApplicationInstanceId"]
    )
