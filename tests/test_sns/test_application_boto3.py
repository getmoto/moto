from uuid import uuid4

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

from . import sns_aws_verified


@mock_aws
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


@mock_aws
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


@mock_aws
def test_get_missing_platform_application_attributes():
    conn = boto3.client("sns", region_name="us-east-1")
    with pytest.raises(ClientError):
        conn.get_platform_application_attributes(PlatformApplicationArn="a-fake-arn")


@mock_aws
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


@mock_aws
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


@mock_aws
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


@mock_aws
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


@pytest.mark.aws_verified
@sns_aws_verified
def test_create_duplicate_default_platform_endpoint(api_key=None):
    conn = boto3.client("sns", region_name="us-east-1")
    platform_name = str(uuid4())[0:6]
    app_arn = None
    try:
        platform_application = conn.create_platform_application(
            Name=platform_name,
            Platform="GCM",
            Attributes={"PlatformCredential": api_key},
        )
        app_arn = platform_application["PlatformApplicationArn"]

        # Create duplicate endpoints
        arn1 = conn.create_platform_endpoint(
            PlatformApplicationArn=app_arn, Token="token"
        )["EndpointArn"]
        arn2 = conn.create_platform_endpoint(
            PlatformApplicationArn=app_arn, Token="token"
        )["EndpointArn"]

        # Create another duplicate endpoint, just specify the default value
        arn3 = conn.create_platform_endpoint(
            PlatformApplicationArn=app_arn,
            Token="token",
            Attributes={"Enabled": "true"},
        )["EndpointArn"]

        assert arn1 == arn2
        assert arn2 == arn3
    finally:
        if app_arn is not None:
            conn.delete_platform_application(PlatformApplicationArn=app_arn)


@pytest.mark.aws_verified
@sns_aws_verified
def test_create_duplicate_platform_endpoint_with_attrs(api_key=None):
    identity = boto3.client("sts", region_name="us-east-1").get_caller_identity()
    account_id = identity["Account"]

    conn = boto3.client("sns", region_name="us-east-1")
    platform_name = str(uuid4())[0:6]
    application_arn = None
    try:
        platform_application = conn.create_platform_application(
            Name=platform_name,
            Platform="GCM",
            Attributes={"PlatformCredential": api_key},
        )
        application_arn = platform_application["PlatformApplicationArn"]
        assert (
            application_arn
            == f"arn:aws:sns:us-east-1:{account_id}:app/GCM/{platform_name}"
        )

        # WITHOUT custom user data
        resp = conn.create_platform_endpoint(
            PlatformApplicationArn=application_arn,
            Token="token_without_userdata",
            Attributes={"Enabled": "false"},
        )
        endpoint1_arn = resp["EndpointArn"]

        # This operation is idempotent
        resp = conn.create_platform_endpoint(
            PlatformApplicationArn=application_arn,
            Token="token_without_userdata",
            Attributes={"Enabled": "false"},
        )
        assert resp["EndpointArn"] == endpoint1_arn

        # Same token, but with CustomUserData
        with pytest.raises(ClientError) as exc:
            conn.create_platform_endpoint(
                PlatformApplicationArn=application_arn,
                Token="token_without_userdata",
                CustomUserData="some user data",
                Attributes={"Enabled": "false"},
            )
        err = exc.value.response["Error"]
        assert err["Code"] == "InvalidParameter"
        assert (
            err["Message"]
            == f"Invalid parameter: Token Reason: Endpoint {endpoint1_arn} already exists with the same Token, but different attributes."
        )

        # WITH custom user data
        resp = conn.create_platform_endpoint(
            PlatformApplicationArn=application_arn,
            Token="token_with_userdata",
            CustomUserData="some user data",
            Attributes={"Enabled": "false"},
        )
        endpoint2_arn = resp["EndpointArn"]
        assert endpoint2_arn.startswith(
            f"arn:aws:sns:us-east-1:{account_id}:endpoint/GCM/{platform_name}/"
        )

        # Still idempotent
        resp = conn.create_platform_endpoint(
            PlatformApplicationArn=application_arn,
            Token="token_with_userdata",
            CustomUserData="some user data",
            Attributes={"Enabled": "false"},
        )
        assert resp["EndpointArn"] == endpoint2_arn

        # Creating a platform endpoint with different attributes fails
        with pytest.raises(ClientError) as exc:
            conn.create_platform_endpoint(
                PlatformApplicationArn=application_arn,
                Token="token_with_userdata",
                CustomUserData="some user data",
                Attributes={"Enabled": "true"},
            )
        err = exc.value.response["Error"]
        assert err["Code"] == "InvalidParameter"
        assert (
            err["Message"]
            == f"Invalid parameter: Token Reason: Endpoint {endpoint2_arn} already exists with the same Token, but different attributes."
        )

        with pytest.raises(ClientError) as exc:
            conn.create_platform_endpoint(
                PlatformApplicationArn=application_arn + "2",
                Token="unknown_arn",
            )
        err = exc.value.response["Error"]
        assert err["Code"] == "NotFound"
        assert err["Message"] == "PlatformApplication does not exist"
    finally:
        if application_arn is not None:
            conn.delete_platform_application(PlatformApplicationArn=application_arn)


@pytest.mark.aws_verified
@sns_aws_verified
def test_get_list_endpoints_by_platform_application(api_key=None):
    conn = boto3.client("sns", region_name="us-east-1")
    platform_name = str(uuid4())[0:6]
    application_arn = None
    try:
        platform_application = conn.create_platform_application(
            Name=platform_name,
            Platform="GCM",
            Attributes={"PlatformCredential": api_key},
        )
        application_arn = platform_application["PlatformApplicationArn"]

        endpoint = conn.create_platform_endpoint(
            PlatformApplicationArn=application_arn,
            Token="some_unique_id",
            Attributes={"CustomUserData": "some data"},
        )
        endpoint_arn = endpoint["EndpointArn"]

        endpoint_list = conn.list_endpoints_by_platform_application(
            PlatformApplicationArn=application_arn
        )["Endpoints"]

        assert len(endpoint_list) == 1
        assert endpoint_list[0]["Attributes"]["CustomUserData"] == "some data"
        assert endpoint_list[0]["EndpointArn"] == endpoint_arn

        resp = conn.delete_endpoint(EndpointArn=endpoint_arn)
        assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

        # Idempotent operation
        resp = conn.delete_endpoint(EndpointArn=endpoint_arn)
        assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    finally:
        if application_arn is not None:
            conn.delete_platform_application(PlatformApplicationArn=application_arn)

    with pytest.raises(ClientError) as exc:
        conn.list_endpoints_by_platform_application(
            PlatformApplicationArn=application_arn + "2"
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "NotFound"
    assert err["Message"] == "PlatformApplication does not exist"


@mock_aws
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


@pytest.mark.aws_verified
@sns_aws_verified
def test_get_non_existent_endpoint_attributes(
    api_key=None,
):  # pylint: disable=unused-argument
    identity = boto3.client("sts", region_name="us-east-1").get_caller_identity()
    account_id = identity["Account"]

    conn = boto3.client("sns", region_name="us-east-1")
    endpoint_arn = f"arn:aws:sns:us-east-1:{account_id}:endpoint/APNS/my-application/c1f76c42-192a-4e75-b04f-a9268ce2abf3"
    with pytest.raises(conn.exceptions.NotFoundException) as excinfo:
        conn.get_endpoint_attributes(EndpointArn=endpoint_arn)
    error = excinfo.value.response["Error"]
    assert error["Type"] == "Sender"
    assert error["Code"] == "NotFound"
    assert error["Message"] == "Endpoint does not exist"


@mock_aws
def test_get_missing_endpoint_attributes():
    conn = boto3.client("sns", region_name="us-east-1")
    with pytest.raises(ClientError):
        conn.get_endpoint_attributes(EndpointArn="a-fake-arn")


@mock_aws
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


@mock_aws
def test_delete_endpoint():
    conn = boto3.client("sns", region_name="us-east-1")
    platform_application = conn.create_platform_application(
        Name="my-application", Platform="APNS", Attributes={}
    )
    app_arn = platform_application["PlatformApplicationArn"]
    endpoint = conn.create_platform_endpoint(
        PlatformApplicationArn=app_arn,
        Token="some_unique_id",
        CustomUserData="some user data",
        Attributes={"Enabled": "true"},
    )

    endpoints = conn.list_endpoints_by_platform_application(
        PlatformApplicationArn=app_arn
    )["Endpoints"]
    assert len(endpoints) == 1

    conn.delete_endpoint(EndpointArn=endpoint["EndpointArn"])

    endpoints = conn.list_endpoints_by_platform_application(
        PlatformApplicationArn=app_arn
    )["Endpoints"]
    assert len(endpoints) == 0


@mock_aws
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


@pytest.mark.aws_verified
@sns_aws_verified
def test_publish_to_disabled_platform_endpoint(api_key=None):
    conn = boto3.client("sns", region_name="us-east-1")
    platform_name = str(uuid4())[0:6]
    application_arn = None
    try:
        platform_application = conn.create_platform_application(
            Name=platform_name,
            Platform="GCM",
            Attributes={"PlatformCredential": api_key},
        )
        application_arn = platform_application["PlatformApplicationArn"]

        endpoint = conn.create_platform_endpoint(
            PlatformApplicationArn=application_arn,
            Token="some_unique_id",
            Attributes={"Enabled": "false"},
        )
        endpoint_arn = endpoint["EndpointArn"]

        with pytest.raises(ClientError) as exc:
            conn.publish(Message="msg", MessageStructure="json", TargetArn=endpoint_arn)
        err = exc.value.response["Error"]
        assert err["Code"] == "EndpointDisabled"
        assert err["Message"] == "Endpoint is disabled"
    finally:
        if application_arn is not None:
            conn.delete_platform_application(PlatformApplicationArn=application_arn)


@sns_aws_verified
def test_publish_to_deleted_platform_endpoint(api_key=None):
    """
    This used to run against AWS, but they have changed the API, and this currently throws an exception:
        Invalid parameter: Attributes Reason: Platform credentials are invalid

    Need to change this test accordingly

    https://docs.aws.amazon.com/sns/latest/dg/sns-send-custom-platform-specific-payloads-mobile-devices.html

    > Amazon SNS now supports Firebase Cloud Messaging (FCM) HTTP v1 API for sending mobile push notifications to Android devices.
    >
    > March 26, 2024 – Amazon SNS supports FCM HTTP v1 API for Apple devices and Webpush destinations.
    > We recommend that you migrate your existing mobile push applications to the latest FCM HTTP v1 API on or before June 1, 2024 to avoid application disruption.
    """
    conn = boto3.client("sns", region_name="us-east-1")
    platform_name = str(uuid4())[0:6]
    topic_name = "topic_" + str(uuid4())[0:6]
    application_arn = None
    try:
        platform_application = conn.create_platform_application(
            Name=platform_name,
            Platform="GCM",
            Attributes={"PlatformCredential": api_key},
        )
        application_arn = platform_application["PlatformApplicationArn"]

        endpoint_arn = conn.create_platform_endpoint(
            PlatformApplicationArn=application_arn,
            Token="some_unique_id",
            Attributes={"Enabled": "false"},
        )["EndpointArn"]

        topic_arn = conn.create_topic(Name=topic_name)["TopicArn"]

        conn.delete_endpoint(EndpointArn=endpoint_arn)

        with pytest.raises(ClientError) as exc:
            conn.subscribe(
                TopicArn=topic_arn,
                Endpoint=endpoint_arn,
                Protocol="application",
            )
        err = exc.value.response["Error"]
        assert err["Code"] == "InvalidParameter"
        assert (
            err["Message"]
            == f"Invalid parameter: Endpoint Reason: Endpoint does not exist for endpoint arn{endpoint_arn}"
        )
    finally:
        if topic_arn is not None:
            conn.delete_topic(TopicArn=topic_arn)
        if application_arn is not None:
            conn.delete_platform_application(PlatformApplicationArn=application_arn)


@mock_aws
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


@mock_aws
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


@mock_aws
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
