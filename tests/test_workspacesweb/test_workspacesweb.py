"""Unit tests for workspacesweb-supported APIs."""
import re
import boto3

from moto import mock_aws

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html

FAKE_SECURITY_GROUP_IDS = ['sg-0123456789abcdef0']
FAKE_SUBNET_IDS = ['subnet-0123456789abcdef0', 'subnet-abcdef0123456789']
FAKE_TAGS = [
    {
        'Key': 'TestKey',
        'Value': 'TestValue'
    },
]
FAKE_VPC_ID = 'vpc-0123456789abcdef0'
FAKE_KMS_KEY_ID = 'abcd1234-5678-90ab-cdef-FAKEKEY'


@mock_aws
def test_create_network_settings():
    client = boto3.client('workspaces-web', region_name='eu-west-1')
    response = client.create_network_settings(
        securityGroupIds=FAKE_SECURITY_GROUP_IDS,
        subnetIds=FAKE_SUBNET_IDS,
        tags=FAKE_TAGS,
        vpcId=FAKE_VPC_ID
    )
    network_settings_arn = response['networkSettingsArn']
    arn_regex = r'^arn:aws:workspaces-web:eu-west-1:\d{12}:network-settings/[a-f0-9-]+$'
    assert re.match(
        arn_regex, network_settings_arn) is not None, f"ARN {network_settings_arn} does not match expected pattern"


@mock_aws
def test_list_network_settings():
    client = boto3.client("workspaces-web", region_name="ap-southeast-1")
    arn = client.create_network_settings(
        securityGroupIds=FAKE_SECURITY_GROUP_IDS,
        subnetIds=FAKE_SUBNET_IDS,
        tags=FAKE_TAGS,
        vpcId=FAKE_VPC_ID
    )['networkSettingsArn']
    resp = client.list_network_settings()
    assert resp["networkSettings"][0][
        "networkSettingsArn"] == arn, f"Expected ARN {arn} in response"
    assert len(resp['networkSettings']
               ) == 1, f"Expected 1 network settings ARN in response, got {len(resp['networkSettings'])}"


@mock_aws
def test_get_network_settings():
    client = boto3.client("workspaces-web", region_name="ap-southeast-1")
    arn = client.create_network_settings(
        securityGroupIds=FAKE_SECURITY_GROUP_IDS,
        subnetIds=FAKE_SUBNET_IDS,
        tags=FAKE_TAGS,
        vpcId=FAKE_VPC_ID
    )['networkSettingsArn']
    resp = client.get_network_settings(networkSettingsArn=arn)[
        'networkSettings']
    assert resp["networkSettingsArn"] == arn, f"Expected ARN {arn} in response"


@mock_aws
def test_create_browser_settings():
    client = boto3.client("workspaces-web", region_name="eu-west-1")
    resp = client.create_browser_settings()

    raise Exception("NotYetImplemented")


@mock_aws
def test_create_portal():
    client = boto3.client("workspaces-web", region_name="eu-west-1")
    resp = client.create_portal()

    raise Exception("NotYetImplemented")


@mock_aws
def test_list_browser_settings():
    client = boto3.client("workspaces-web", region_name="us-east-2")
    resp = client.list_browser_settings()

    raise Exception("NotYetImplemented")


@mock_aws
def test_list_portals():
    client = boto3.client("workspaces-web", region_name="eu-west-1")
    resp = client.list_portals()

    raise Exception("NotYetImplemented")


@mock_aws
def test_get_browser_settings():
    client = boto3.client("workspaces-web", region_name="us-east-2")
    resp = client.get_browser_settings()

    raise Exception("NotYetImplemented")


@mock_aws
def test_delete_browser_settings():
    client = boto3.client("workspaces-web", region_name="eu-west-1")
    resp = client.delete_browser_settings()

    raise Exception("NotYetImplemented")


@mock_aws
def test_delete_network_settings():
    client = boto3.client("workspaces-web", region_name="eu-west-1")
    resp = client.delete_network_settings()

    raise Exception("NotYetImplemented")


@mock_aws
def test_get_portal():
    client = boto3.client("workspaces-web", region_name="eu-west-1")
    resp = client.get_portal()

    raise Exception("NotYetImplemented")


@mock_aws
def test_get_portal():
    client = boto3.client("workspaces-web", region_name="ap-southeast-1")
    resp = client.get_portal()

    raise Exception("NotYetImplemented")


@mock_aws
def test_delete_portal():
    client = boto3.client("workspaces-web", region_name="ap-southeast-1")
    resp = client.delete_portal()

    raise Exception("NotYetImplemented")


@mock_aws
def test_associate_browser_settings():
    client = boto3.client("workspaces-web", region_name="us-east-2")
    resp = client.associate_browser_settings()

    raise Exception("NotYetImplemented")


@mock_aws
def test_associate_network_settings():
    client = boto3.client("workspaces-web", region_name="ap-southeast-1")
    resp = client.associate_network_settings()

    raise Exception("NotYetImplemented")
