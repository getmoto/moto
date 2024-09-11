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
def test_delete_network_settings():
    client = boto3.client('workspaces-web', region_name='eu-west-1')
    arn = client.create_network_settings(
        securityGroupIds=FAKE_SECURITY_GROUP_IDS,
        subnetIds=FAKE_SUBNET_IDS,
        tags=FAKE_TAGS,
        vpcId=FAKE_VPC_ID
    )['networkSettingsArn']
    client.delete_network_settings(networkSettingsArn=arn)
    resp = client.list_network_settings()
    assert len(resp['networkSettings'] == 0), "Expected no network settings"


@mock_aws
def test_create_browser_settings():
    client = boto3.client("workspaces-web", region_name="eu-west-1")
    response = client.create_browser_settings(
        additionalEncryptionContext={"Key1": "Value1", "Key2": "Value2"},
        browserPolicy="TestBrowserPolicy",
        clientToken="TestClient",
        customerManagedKey=FAKE_KMS_KEY_ID,
        tags=FAKE_TAGS
    )
    browser_settings_arn = response['browserSettingsArn']
    arn_regex = r'^arn:aws:workspaces-web:eu-west-1:\d{12}:browser-settings/[a-f0-9-]+$'
    assert re.match(
        arn_regex, browser_settings_arn) is not None, f"ARN {browser_settings_arn} does not match expected pattern"


@mock_aws
def test_list_browser_settings():
    client = boto3.client("workspaces-web", region_name="eu-west-1")
    arn = client.create_browser_settings(
        additionalEncryptionContext={"Key1": "Value1", "Key2": "Value2"},
        browserPolicy="TestBrowserPolicy",
        clientToken="TestClient",
        customerManagedKey=FAKE_KMS_KEY_ID,
        tags=FAKE_TAGS
    )['browserSettingsArn']
    resp = client.list_browser_settings()
    assert resp["browserSettings"][0][
        "browserSettingsArn"] == arn, f"Expected ARN {arn} in response"


@mock_aws
def test_get_browser_settings():
    client = boto3.client("workspaces-web", region_name="eu-west-1")
    arn = client.create_browser_settings(
        additionalEncryptionContext={"Key1": "Value1", "Key2": "Value2"},
        browserPolicy="TestBrowserPolicy",
        clientToken="TestClient",
        customerManagedKey=FAKE_KMS_KEY_ID,
        tags=FAKE_TAGS
    )["browserSettingsArn"]
    resp = client.get_browser_settings(browserSettingsArn=arn)[
        "browserSettings"]
    assert resp["browserSettingsArn"] == arn, f"Expected ARN {arn} in response"


@mock_aws
def test_delete_browser_settings():
    client = boto3.client("workspaces-web", region_name="eu-west-1")
    arn = client.create_browser_settings(
        additionalEncryptionContext={"Key1": "Value1", "Key2": "Value2"},
        browserPolicy="TestBrowserPolicy",
        clientToken="TestClient",
        customerManagedKey=FAKE_KMS_KEY_ID,
        tags=FAKE_TAGS
    )["browserSettingsArn"]
    client.delete_browser_settings(browserSettingsArn=arn)
    resp = client.list_browser_settings()
    assert len(resp["browserSettings"]) == 0, "Expected no browser settings"


@mock_aws
def test_create_portal():
    client = boto3.client("workspaces-web", region_name="eu-west-1")
    resp = client.create_portal(
        additionalEncryptionContext={"Key1": "Value1", "Key2": "Value2"},
        authenticationType="Standard",
        clientToken="TestClient",
        customerManagedKey=FAKE_KMS_KEY_ID,
        displayName="TestDisplayName",
        instanceType="TestInstanceType",
        maxConcurrentSessions=5,
        tags=FAKE_TAGS
    )
    assert resp["portalArn"] is not None, "Expected portal ARN in response"
    assert resp["portalEndpoint"] is not None, "Expected portal endpoint in response"


@mock_aws
def test_list_portals():
    client = boto3.client("workspaces-web", region_name="eu-west-1")
    arn = client.create_portal(
        additionalEncryptionContext={"Key1": "Value1", "Key2": "Value2"},
        authenticationType="Standard",
        clientToken="TestClient",
        customerManagedKey=FAKE_KMS_KEY_ID,
        displayName="TestDisplayName",
        instanceType="TestInstanceType",
        maxConcurrentSessions=5,
        tags=FAKE_TAGS
    )['portalArn']
    resp = client.list_portals()
    assert resp["portals"][0]["portalArn"] == arn, f"Expected ARN {arn} in response"
    assert len(
        resp['portals']) == 1, f"Expected 1 portal ARN in response, got {len(resp['portals'])}"
    assert resp['portals'][0]['authenticationType'] == "Standard", "Expected authentication type in response"


@mock_aws
def test_get_portal():
    client = boto3.client("workspaces-web", region_name="eu-west-1")
    arn = client.create_portal(
        additionalEncryptionContext={"Key1": "Value1", "Key2": "Value2"},
        authenticationType="Standard",
        clientToken="TestClient",
        customerManagedKey=FAKE_KMS_KEY_ID,
        displayName="TestDisplayName",
        instanceType="TestInstanceType",
        maxConcurrentSessions=5,
        tags=FAKE_TAGS
    )["portalArn"]
    resp = client.get_portal(portalArn=arn)["portal"]
    assert resp["portalArn"] == arn, f"Expected ARN {arn} in response"
    assert resp["authenticationType"] == "Standard", "Expected authentication type in response"
    assert resp["instanceType"] == "TestInstanceType", "Expected instance type in response"
    assert resp["maxConcurrentSessions"] == 5, "Expected max concurrent sessions in response"


@mock_aws
def test_delete_portal():
    client = boto3.client("workspaces-web", region_name="eu-west-1")
    arn = client.create_portal(
        additionalEncryptionContext={"Key1": "Value1", "Key2": "Value2"},
        authenticationType="Standard",
        clientToken="TestClient",
        customerManagedKey=FAKE_KMS_KEY_ID,
        displayName="TestDisplayName",
        instanceType="TestInstanceType",
        maxConcurrentSessions=5,
        tags=FAKE_TAGS
    )["portalArn"]
    client.delete_portal(portalArn=arn)
    assert len(client.list_portals()["portals"]) == 0, "Expected no portals"


@mock_aws
def test_associate_browser_settings():
    client = boto3.client("workspaces-web", region_name="eu-west-1")
    browser_settings_arn = client.create_browser_settings(
        additionalEncryptionContext={"Key1": "Value1", "Key2": "Value2"},
        browserPolicy="TestBrowserPolicy",
        clientToken="TestClient",
        customerManagedKey=FAKE_KMS_KEY_ID,
        tags=FAKE_TAGS
    )["browserSettingsArn"]
    portal_arn = client.create_portal(
        additionalEncryptionContext={"Key1": "Value1", "Key2": "Value2"},
        authenticationType="Standard",
        clientToken="TestClient",
        customerManagedKey=FAKE_KMS_KEY_ID,
        displayName="TestDisplayName",
        instanceType="TestInstanceType",
        maxConcurrentSessions=5,
        tags=FAKE_TAGS
    )["portalArn"]
    client.associate_browser_settings(
        browserSettingsArn=browser_settings_arn, portalArn=portal_arn)
    resp = client.get_portal(portalArn=portal_arn)["portal"]
    assert resp[
        "associatedBrowserSettingsArn"] == browser_settings_arn, f"Expected associated browser settings ARN {browser_settings_arn} in response"
    resp = client.get_browser_settings(browserSettingsArn=browser_settings_arn)
    assert resp[
        "associatedPortals"] == [portal_arn], f"Expected associated portal ARN {portal_arn} in response"


@mock_aws
def test_associate_network_settings():
    client = boto3.client("workspaces-web", region_name="eu-west-1")
    network_arn = client.create_network_settings(
        securityGroupIds=FAKE_SECURITY_GROUP_IDS,
        subnetIds=FAKE_SUBNET_IDS,
        tags=FAKE_TAGS,
        vpcId=FAKE_VPC_ID
    )['networkSettingsArn']
    portal_arn = client.create_portal(
        additionalEncryptionContext={"Key1": "Value1", "Key2": "Value2"},
        authenticationType="Standard",
        clientToken="TestClient",
        customerManagedKey=FAKE_KMS_KEY_ID,
        displayName="TestDisplayName",
        instanceType="TestInstanceType",
        maxConcurrentSessions=5,
        tags=FAKE_TAGS
    )["portalArn"]
    print("Portal ARN: ", portal_arn)
    client.associate_network_settings(
        networkSettingsArn=network_arn, portalArn=portal_arn)
    resp = client.get_portal(portalArn=portal_arn)["portal"]
    assert resp[
        "associatedNetworkSettingsArn"] == network_arn, f"Expected associated network settings ARN {network_arn} in response"
    resp = client.get_network_settings(networkSettingsArn=network_arn)
    assert resp[
        "associatedPortals"] == [portal_arn], f"Expected associated portal ARN {portal_arn} in response"
