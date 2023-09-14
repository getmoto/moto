import boto3
from botocore.exceptions import ClientError
import pytest

from moto import mock_sns
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID


@mock_sns
def test_create_platform_application():
    conn = boto3.client("sns", region_name="us-east-1")
    response = conn.create_platform_application(
        Name="my-application",
        Platform="APNS",
        Attributes={
            "PlatformCredential": "platform_credential",
            "PlatformPrincipal": "platform_principal",
        },
    )
    application_arn = response["PlatformApplicationArn"]
    assert application_arn == (
        f"arn:aws:sns:us-east-1:{ACCOUNT_ID}:app/APNS/my-application"
    )


@mock_sns
def test_get_platform_application_attributes():
    conn = boto3.client("sns", region_name="us-east-1")
    platform_application = conn.create_platform_application(
        Name="my-application",
        Platform="APNS",
        Attributes={
            "PlatformCredential": "platform_credential",
            "PlatformPrincipal": "platform_principal",
        },
    )
    arn = platform_application["PlatformApplicationArn"]
    attributes = conn.get_platform_application_attributes(PlatformApplicationArn=arn)[
        "Attributes"
    ]
    assert attributes == {
        "PlatformCredential": "platform_credential",
        "PlatformPrincipal": "platform_principal",
    }


@mock_sns
def test_get_missing_platform_application_attributes():
    conn = boto3.client("sns", region_name="us-east-1")
    with pytest.raises(ClientError):
        conn.get_platform_application_attributes(PlatformApplicationArn="a-fake-arn")


@mock_sns
def test_set_platform_application_attributes():
    conn = boto3.client("sns", region_name="us-east-1")
    platform_application = conn.create_platform_application(
        Name="my-application",
        Platform="APNS",
        Attributes={
            "PlatformCredential": "platform_credential",
            "PlatformPrincipal": "platform_principal",
        },
    )
    arn = platform_application["PlatformApplicationArn"]
    conn.set_platform_application_attributes(
        PlatformApplicationArn=arn, Attributes={"PlatformPrincipal": "other"}
    )
    attributes = conn.get_platform_application_attributes(PlatformApplicationArn=arn)[
        "Attributes"
    ]
    assert attributes == (
        {"PlatformCredential": "platform_credential", "PlatformPrincipal": "other"}
    )


@mock_sns
def test_list_platform_applications():
    conn = boto3.client("sns", region_name="us-east-1")
    conn.create_platform_application(
        Name="application1", Platform="APNS", Attributes={}
    )
    conn.create_platform_application(
        Name="application2", Platform="APNS", Attributes={}
    )

    applications_response = conn.list_platform_applications()
    applications = applications_response["PlatformApplications"]
    assert len(applications) == 2


@mock_sns
def test_delete_platform_application():
    conn = boto3.client("sns", region_name="us-east-1")
    conn.create_platform_application(
        Name="application1", Platform="APNS", Attributes={}
    )
    conn.create_platform_application(
        Name="application2", Platform="APNS", Attributes={}
    )

    applications_response = conn.list_platform_applications()
    applications = applications_response["PlatformApplications"]
    assert len(applications) == 2

    application_arn = applications[0]["PlatformApplicationArn"]
    conn.delete_platform_application(PlatformApplicationArn=application_arn)

    applications_response = conn.list_platform_applications()
    applications = applications_response["PlatformApplications"]
    assert len(applications) == 1


@mock_sns
def test_create_platform_endpoint():
    conn = boto3.client("sns", region_name="us-east-1")
    platform_application = conn.create_platform_application(
        Name="my-application", Platform="APNS", Attributes={}
    )
    application_arn = platform_application["PlatformApplicationArn"]

    endpoint = conn.create_platform_endpoint(
        PlatformApplicationArn=application_arn,
        Token="some_unique_id",
        CustomUserData="some user data",
        Attributes={"Enabled": "false"},
    )

    endpoint_arn = endpoint["EndpointArn"]
    assert (
        f"arn:aws:sns:us-east-1:{ACCOUNT_ID}:endpoint/APNS/my-application/"
        in endpoint_arn
    )


@mock_sns
def test_create_duplicate_platform_endpoint():
    conn = boto3.client("sns", region_name="us-east-1")
    platform_application = conn.create_platform_application(
        Name="my-application", Platform="APNS", Attributes={}
    )
    application_arn = platform_application["PlatformApplicationArn"]

    conn.create_platform_endpoint(
        PlatformApplicationArn=application_arn,
        Token="some_unique_id",
        CustomUserData="some user data",
        Attributes={"Enabled": "false"},
    )

    with pytest.raises(ClientError):
        conn.create_platform_endpoint(
            PlatformApplicationArn=application_arn,
            Token="some_unique_id",
            CustomUserData="some user data",
            Attributes={"Enabled": "true"},
        )


@mock_sns
def test_create_duplicate_platform_endpoint_with_same_attributes():
    conn = boto3.client("sns", region_name="us-east-1")
    platform_application = conn.create_platform_application(
        Name="my-application", Platform="APNS", Attributes={}
    )
    application_arn = platform_application["PlatformApplicationArn"]

    created_endpoint = conn.create_platform_endpoint(
        PlatformApplicationArn=application_arn,
        Token="some_unique_id",
        CustomUserData="some user data",
        Attributes={"Enabled": "false"},
    )
    created_endpoint_arn = created_endpoint["EndpointArn"]

    endpoint = conn.create_platform_endpoint(
        PlatformApplicationArn=application_arn,
        Token="some_unique_id",
        CustomUserData="some user data",
        Attributes={"Enabled": "false"},
    )
    endpoint_arn = endpoint["EndpointArn"]

    assert endpoint_arn == created_endpoint_arn


@mock_sns
def test_get_list_endpoints_by_platform_application():
    conn = boto3.client("sns", region_name="us-east-1")
    platform_application = conn.create_platform_application(
        Name="my-application", Platform="APNS", Attributes={}
    )
    application_arn = platform_application["PlatformApplicationArn"]

    endpoint = conn.create_platform_endpoint(
        PlatformApplicationArn=application_arn,
        Token="some_unique_id",
        CustomUserData="some user data",
        Attributes={"CustomUserData": "some data"},
    )
    endpoint_arn = endpoint["EndpointArn"]

    endpoint_list = conn.list_endpoints_by_platform_application(
        PlatformApplicationArn=application_arn
    )["Endpoints"]

    assert len(endpoint_list) == 1
    assert endpoint_list[0]["Attributes"]["CustomUserData"] == "some data"
    assert endpoint_list[0]["EndpointArn"] == endpoint_arn


@mock_sns
def test_get_endpoint_attributes():
    conn = boto3.client("sns", region_name="us-east-1")
    platform_application = conn.create_platform_application(
        Name="my-application", Platform="APNS", Attributes={}
    )
    application_arn = platform_application["PlatformApplicationArn"]

    endpoint = conn.create_platform_endpoint(
        PlatformApplicationArn=application_arn,
        Token="some_unique_id",
        CustomUserData="some user data",
        Attributes={"Enabled": "false", "CustomUserData": "some data"},
    )
    endpoint_arn = endpoint["EndpointArn"]

    attributes = conn.get_endpoint_attributes(EndpointArn=endpoint_arn)["Attributes"]
    assert attributes == (
        {"Token": "some_unique_id", "Enabled": "false", "CustomUserData": "some data"}
    )


@mock_sns
def test_get_non_existent_endpoint_attributes():
    conn = boto3.client("sns", region_name="us-east-1")
    endpoint_arn = (
        "arn:aws:sns:us-east-1:123456789012:endpoint/APNS/my-application"
        "/c1f76c42-192a-4e75-b04f-a9268ce2abf3"
    )
    with pytest.raises(conn.exceptions.NotFoundException) as excinfo:
        conn.get_endpoint_attributes(EndpointArn=endpoint_arn)
    error = excinfo.value.response["Error"]
    assert error["Type"] == "Sender"
    assert error["Code"] == "NotFound"
    assert error["Message"] == "Endpoint does not exist"


@mock_sns
def test_get_missing_endpoint_attributes():
    conn = boto3.client("sns", region_name="us-east-1")
    with pytest.raises(ClientError):
        conn.get_endpoint_attributes(EndpointArn="a-fake-arn")


@mock_sns
def test_set_endpoint_attributes():
    conn = boto3.client("sns", region_name="us-east-1")
    platform_application = conn.create_platform_application(
        Name="my-application", Platform="APNS", Attributes={}
    )
    application_arn = platform_application["PlatformApplicationArn"]

    endpoint = conn.create_platform_endpoint(
        PlatformApplicationArn=application_arn,
        Token="some_unique_id",
        CustomUserData="some user data",
        Attributes={"Enabled": "false", "CustomUserData": "some data"},
    )
    endpoint_arn = endpoint["EndpointArn"]

    conn.set_endpoint_attributes(
        EndpointArn=endpoint_arn, Attributes={"CustomUserData": "other data"}
    )
    attributes = conn.get_endpoint_attributes(EndpointArn=endpoint_arn)["Attributes"]
    assert attributes == (
        {"Token": "some_unique_id", "Enabled": "false", "CustomUserData": "other data"}
    )


@mock_sns
def test_delete_endpoint():
    conn = boto3.client("sns", region_name="us-east-1")
    platform_application = conn.create_platform_application(
        Name="my-application", Platform="APNS", Attributes={}
    )
    application_arn = platform_application["PlatformApplicationArn"]
    endpoint = conn.create_platform_endpoint(
        PlatformApplicationArn=application_arn,
        Token="some_unique_id",
        CustomUserData="some user data",
        Attributes={"Enabled": "true"},
    )

    assert (
        len(
            conn.list_endpoints_by_platform_application(
                PlatformApplicationArn=application_arn
            )["Endpoints"]
        )
        == 1
    )

    conn.delete_endpoint(EndpointArn=endpoint["EndpointArn"])

    assert (
        len(
            conn.list_endpoints_by_platform_application(
                PlatformApplicationArn=application_arn
            )["Endpoints"]
        )
        == 0
    )


@mock_sns
def test_publish_to_platform_endpoint():
    conn = boto3.client("sns", region_name="us-east-1")
    platform_application = conn.create_platform_application(
        Name="my-application", Platform="APNS", Attributes={}
    )
    application_arn = platform_application["PlatformApplicationArn"]

    endpoint = conn.create_platform_endpoint(
        PlatformApplicationArn=application_arn,
        Token="some_unique_id",
        CustomUserData="some user data",
        Attributes={"Enabled": "true"},
    )

    endpoint_arn = endpoint["EndpointArn"]

    conn.publish(
        Message="some message", MessageStructure="json", TargetArn=endpoint_arn
    )


@mock_sns
def test_publish_to_disabled_platform_endpoint():
    conn = boto3.client("sns", region_name="us-east-1")
    platform_application = conn.create_platform_application(
        Name="my-application", Platform="APNS", Attributes={}
    )
    application_arn = platform_application["PlatformApplicationArn"]

    endpoint = conn.create_platform_endpoint(
        PlatformApplicationArn=application_arn,
        Token="some_unique_id",
        CustomUserData="some user data",
        Attributes={"Enabled": "false"},
    )

    endpoint_arn = endpoint["EndpointArn"]

    with pytest.raises(ClientError):
        conn.publish(
            Message="some message", MessageStructure="json", TargetArn=endpoint_arn
        )


@mock_sns
def test_set_sms_attributes():
    conn = boto3.client("sns", region_name="us-east-1")

    conn.set_sms_attributes(
        attributes={"DefaultSMSType": "Transactional", "test": "test"}
    )

    response = conn.get_sms_attributes()
    assert "attributes" in response
    assert "DefaultSMSType" in response["attributes"]
    assert "test" in response["attributes"]
    assert response["attributes"]["DefaultSMSType"] == "Transactional"
    assert response["attributes"]["test"] == "test"


@mock_sns
def test_get_sms_attributes_filtered():
    conn = boto3.client("sns", region_name="us-east-1")

    conn.set_sms_attributes(
        attributes={"DefaultSMSType": "Transactional", "test": "test"}
    )

    response = conn.get_sms_attributes(attributes=["DefaultSMSType"])
    assert "attributes" in response
    assert "DefaultSMSType" in response["attributes"]
    assert "test" not in response["attributes"]
    assert response["attributes"]["DefaultSMSType"] == "Transactional"


@mock_sns
def test_delete_endpoints_of_delete_app():
    conn = boto3.client("sns", region_name="us-east-1")

    platform_app_arn = conn.create_platform_application(
        Name="app-test-kevs", Platform="GCM", Attributes={"PlatformCredential": "test"}
    )["PlatformApplicationArn"]

    endpoint_arn = conn.create_platform_endpoint(
        PlatformApplicationArn=platform_app_arn,
        Token="test",
    )["EndpointArn"]

    conn.delete_platform_application(PlatformApplicationArn=platform_app_arn)

    with pytest.raises(conn.exceptions.NotFoundException) as excinfo:
        conn.get_endpoint_attributes(EndpointArn=endpoint_arn)
    error = excinfo.value.response["Error"]
    assert error["Type"] == "Sender"
    assert error["Code"] == "NotFound"
    assert error["Message"] == "Endpoint does not exist"
