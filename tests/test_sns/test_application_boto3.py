from __future__ import unicode_literals

import boto3
from botocore.exceptions import ClientError
from moto import mock_sns
import sure  # noqa


@mock_sns
def test_create_platform_application():
    conn = boto3.client('sns', region_name='us-east-1')
    response = conn.create_platform_application(
        Name="my-application",
        Platform="APNS",
        Attributes={
            "PlatformCredential": "platform_credential",
            "PlatformPrincipal": "platform_principal",
        },
    )
    application_arn = response['PlatformApplicationArn']
    application_arn.should.equal(
        'arn:aws:sns:us-east-1:123456789012:app/APNS/my-application')


@mock_sns
def test_get_platform_application_attributes():
    conn = boto3.client('sns', region_name='us-east-1')
    platform_application = conn.create_platform_application(
        Name="my-application",
        Platform="APNS",
        Attributes={
            "PlatformCredential": "platform_credential",
            "PlatformPrincipal": "platform_principal",
        },
    )
    arn = platform_application['PlatformApplicationArn']
    attributes = conn.get_platform_application_attributes(
        PlatformApplicationArn=arn)['Attributes']
    attributes.should.equal({
        "PlatformCredential": "platform_credential",
        "PlatformPrincipal": "platform_principal",
    })


@mock_sns
def test_get_missing_platform_application_attributes():
    conn = boto3.client('sns', region_name='us-east-1')
    conn.get_platform_application_attributes.when.called_with(
        PlatformApplicationArn="a-fake-arn").should.throw(ClientError)


@mock_sns
def test_set_platform_application_attributes():
    conn = boto3.client('sns', region_name='us-east-1')
    platform_application = conn.create_platform_application(
        Name="my-application",
        Platform="APNS",
        Attributes={
            "PlatformCredential": "platform_credential",
            "PlatformPrincipal": "platform_principal",
        },
    )
    arn = platform_application['PlatformApplicationArn']
    conn.set_platform_application_attributes(PlatformApplicationArn=arn,
                                             Attributes={
                                                 "PlatformPrincipal": "other"}
                                             )
    attributes = conn.get_platform_application_attributes(
        PlatformApplicationArn=arn)['Attributes']
    attributes.should.equal({
        "PlatformCredential": "platform_credential",
        "PlatformPrincipal": "other",
    })


@mock_sns
def test_list_platform_applications():
    conn = boto3.client('sns', region_name='us-east-1')
    conn.create_platform_application(
        Name="application1",
        Platform="APNS",
        Attributes={},
    )
    conn.create_platform_application(
        Name="application2",
        Platform="APNS",
        Attributes={},
    )

    applications_repsonse = conn.list_platform_applications()
    applications = applications_repsonse['PlatformApplications']
    applications.should.have.length_of(2)


@mock_sns
def test_delete_platform_application():
    conn = boto3.client('sns', region_name='us-east-1')
    conn.create_platform_application(
        Name="application1",
        Platform="APNS",
        Attributes={},
    )
    conn.create_platform_application(
        Name="application2",
        Platform="APNS",
        Attributes={},
    )

    applications_repsonse = conn.list_platform_applications()
    applications = applications_repsonse['PlatformApplications']
    applications.should.have.length_of(2)

    application_arn = applications[0]['PlatformApplicationArn']
    conn.delete_platform_application(PlatformApplicationArn=application_arn)

    applications_repsonse = conn.list_platform_applications()
    applications = applications_repsonse['PlatformApplications']
    applications.should.have.length_of(1)


@mock_sns
def test_create_platform_endpoint():
    conn = boto3.client('sns', region_name='us-east-1')
    platform_application = conn.create_platform_application(
        Name="my-application",
        Platform="APNS",
        Attributes={},
    )
    application_arn = platform_application['PlatformApplicationArn']

    endpoint = conn.create_platform_endpoint(
        PlatformApplicationArn=application_arn,
        Token="some_unique_id",
        CustomUserData="some user data",
        Attributes={
            "Enabled": 'false',
        },
    )

    endpoint_arn = endpoint['EndpointArn']
    endpoint_arn.should.contain(
        "arn:aws:sns:us-east-1:123456789012:endpoint/APNS/my-application/")


@mock_sns
def test_create_duplicate_platform_endpoint():
    conn = boto3.client('sns', region_name='us-east-1')
    platform_application = conn.create_platform_application(
        Name="my-application",
        Platform="APNS",
        Attributes={},
    )
    application_arn = platform_application['PlatformApplicationArn']

    endpoint = conn.create_platform_endpoint(
        PlatformApplicationArn=application_arn,
        Token="some_unique_id",
        CustomUserData="some user data",
        Attributes={
            "Enabled": 'false',
        },
    )

    endpoint = conn.create_platform_endpoint.when.called_with(
        PlatformApplicationArn=application_arn,
        Token="some_unique_id",
        CustomUserData="some user data",
        Attributes={
            "Enabled": 'false',
        },
    ).should.throw(ClientError)


@mock_sns
def test_get_list_endpoints_by_platform_application():
    conn = boto3.client('sns', region_name='us-east-1')
    platform_application = conn.create_platform_application(
        Name="my-application",
        Platform="APNS",
        Attributes={},
    )
    application_arn = platform_application['PlatformApplicationArn']

    endpoint = conn.create_platform_endpoint(
        PlatformApplicationArn=application_arn,
        Token="some_unique_id",
        CustomUserData="some user data",
        Attributes={
            "CustomUserData": "some data",
        },
    )
    endpoint_arn = endpoint['EndpointArn']

    endpoint_list = conn.list_endpoints_by_platform_application(
        PlatformApplicationArn=application_arn
    )['Endpoints']

    endpoint_list.should.have.length_of(1)
    endpoint_list[0]['Attributes']['CustomUserData'].should.equal('some data')
    endpoint_list[0]['EndpointArn'].should.equal(endpoint_arn)


@mock_sns
def test_get_endpoint_attributes():
    conn = boto3.client('sns', region_name='us-east-1')
    platform_application = conn.create_platform_application(
        Name="my-application",
        Platform="APNS",
        Attributes={},
    )
    application_arn = platform_application['PlatformApplicationArn']

    endpoint = conn.create_platform_endpoint(
        PlatformApplicationArn=application_arn,
        Token="some_unique_id",
        CustomUserData="some user data",
        Attributes={
            "Enabled": 'false',
            "CustomUserData": "some data",
        },
    )
    endpoint_arn = endpoint['EndpointArn']

    attributes = conn.get_endpoint_attributes(
        EndpointArn=endpoint_arn)['Attributes']
    attributes.should.equal({
        "Token": "some_unique_id",
        "Enabled": 'false',
        "CustomUserData": "some data",
    })


@mock_sns
def test_get_missing_endpoint_attributes():
    conn = boto3.client('sns', region_name='us-east-1')
    conn.get_endpoint_attributes.when.called_with(
        EndpointArn="a-fake-arn").should.throw(ClientError)


@mock_sns
def test_set_endpoint_attributes():
    conn = boto3.client('sns', region_name='us-east-1')
    platform_application = conn.create_platform_application(
        Name="my-application",
        Platform="APNS",
        Attributes={},
    )
    application_arn = platform_application['PlatformApplicationArn']

    endpoint = conn.create_platform_endpoint(
        PlatformApplicationArn=application_arn,
        Token="some_unique_id",
        CustomUserData="some user data",
        Attributes={
            "Enabled": 'false',
            "CustomUserData": "some data",
        },
    )
    endpoint_arn = endpoint['EndpointArn']

    conn.set_endpoint_attributes(EndpointArn=endpoint_arn,
                                 Attributes={"CustomUserData": "other data"}
                                 )
    attributes = conn.get_endpoint_attributes(
        EndpointArn=endpoint_arn)['Attributes']
    attributes.should.equal({
        "Token": "some_unique_id",
        "Enabled": 'false',
        "CustomUserData": "other data",
    })


@mock_sns
def test_publish_to_platform_endpoint():
    conn = boto3.client('sns', region_name='us-east-1')
    platform_application = conn.create_platform_application(
        Name="my-application",
        Platform="APNS",
        Attributes={},
    )
    application_arn = platform_application['PlatformApplicationArn']

    endpoint = conn.create_platform_endpoint(
        PlatformApplicationArn=application_arn,
        Token="some_unique_id",
        CustomUserData="some user data",
        Attributes={
            "Enabled": 'true',
        },
    )

    endpoint_arn = endpoint['EndpointArn']

    conn.publish(Message="some message",
                 MessageStructure="json", TargetArn=endpoint_arn)


@mock_sns
def test_publish_to_disabled_platform_endpoint():
    conn = boto3.client('sns', region_name='us-east-1')
    platform_application = conn.create_platform_application(
        Name="my-application",
        Platform="APNS",
        Attributes={},
    )
    application_arn = platform_application['PlatformApplicationArn']

    endpoint = conn.create_platform_endpoint(
        PlatformApplicationArn=application_arn,
        Token="some_unique_id",
        CustomUserData="some user data",
        Attributes={
            "Enabled": 'false',
        },
    )

    endpoint_arn = endpoint['EndpointArn']

    conn.publish.when.called_with(
        Message="some message",
        MessageStructure="json",
        TargetArn=endpoint_arn,
    ).should.throw(ClientError)


@mock_sns
def test_set_sms_attributes():
    conn = boto3.client('sns', region_name='us-east-1')

    conn.set_sms_attributes(attributes={'DefaultSMSType': 'Transactional', 'test': 'test'})

    response = conn.get_sms_attributes()
    response.should.contain('attributes')
    response['attributes'].should.contain('DefaultSMSType')
    response['attributes'].should.contain('test')
    response['attributes']['DefaultSMSType'].should.equal('Transactional')
    response['attributes']['test'].should.equal('test')


@mock_sns
def test_get_sms_attributes_filtered():
    conn = boto3.client('sns', region_name='us-east-1')

    conn.set_sms_attributes(attributes={'DefaultSMSType': 'Transactional', 'test': 'test'})

    response = conn.get_sms_attributes(attributes=['DefaultSMSType'])
    response.should.contain('attributes')
    response['attributes'].should.contain('DefaultSMSType')
    response['attributes'].should_not.contain('test')
    response['attributes']['DefaultSMSType'].should.equal('Transactional')
