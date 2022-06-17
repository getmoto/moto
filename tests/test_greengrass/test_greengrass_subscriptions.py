import boto3
from botocore.client import ClientError
import freezegun
import pytest

from moto import mock_greengrass
from moto.core import get_account_id
from moto.settings import TEST_SERVER_MODE

ACCOUNT_ID = get_account_id()


@pytest.mark.parametrize(
    "target",
    [
        "cloud",
        "GGShadowService",
        "arn:aws:iot:ap-northeast-1:123456789012:thing/2ec8d399c34e1e3fe8da266559adcb7e47c989aab353bc0fc7d0f4bad66030ff",
        "arn:aws:lambda:ap-northeast-1:123456789012:function:test-func:v1",
    ],
)
@freezegun.freeze_time("2022-06-01 12:00:00")
@mock_greengrass
def test_create_subscription_definition(target):

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    init_ver = {
        "Subscriptions": [
            {
                "Id": "123456",
                "Source": "arn:aws:lambda:ap-northeast-1:123456789012:function:test_func:1",
                "Subject": "foo/bar",
                "Target": target,
            }
        ]
    }
    subscription_name = "TestSubscription"
    res = client.create_subscription_definition(
        InitialVersion=init_ver, Name=subscription_name
    )
    res.should.have.key("Arn")
    res.should.have.key("Id")
    res.should.have.key("LatestVersion")
    res.should.have.key("LatestVersionArn")
    res.should.have.key("Name").equals(subscription_name)
    res["ResponseMetadata"]["HTTPStatusCode"].should.equal(201)

    if not TEST_SERVER_MODE:
        res.should.have.key("CreationTimestamp").equals("2022-06-01T12:00:00.000Z")
        res.should.have.key("LastUpdatedTimestamp").equals("2022-06-01T12:00:00.000Z")


@mock_greengrass
def test_create_subscription_definition_with_invalid_target():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    init_ver = {
        "Subscriptions": [
            {
                "Id": "123456",
                "Source": "arn:aws:lambda:ap-northeast-1:123456789012:function:test_func:1",
                "Subject": "foo/bar",
                "Target": "foo",
            }
        ]
    }
    with pytest.raises(ClientError) as ex:
        client.create_subscription_definition(
            InitialVersion=init_ver, Name="TestSubscription"
        )

    ex.value.response["Error"]["Message"].should.equal(
        "The subscriptions definition is invalid or corrupted. (ErrorDetails: [Subscription target is invalid. ID is '123456' and Target is 'foo'])"
    )
    ex.value.response["Error"]["Code"].should.equal("400")


@mock_greengrass
def test_create_subscription_definition_with_invalid_source():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    init_ver = {
        "Subscriptions": [
            {
                "Id": "123456",
                "Source": "foo",
                "Subject": "foo/bar",
                "Target": "arn:aws:lambda:ap-northeast-1:123456789012:function:test_func:1",
            }
        ]
    }
    with pytest.raises(ClientError) as ex:
        client.create_subscription_definition(
            InitialVersion=init_ver, Name="TestSubscription"
        )

    ex.value.response["Error"]["Message"].should.equal(
        "The subscriptions definition is invalid or corrupted. (ErrorDetails: [Subscription source is invalid. ID is '123456' and Source is 'foo'])"
    )
    ex.value.response["Error"]["Code"].should.equal("400")


@freezegun.freeze_time("2022-06-01 12:00:00")
@mock_greengrass
def test_list_subscription_definitions():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    init_ver = {
        "Subscriptions": [
            {
                "Id": "123456",
                "Source": "arn:aws:lambda:ap-northeast-1:123456789012:function:test_func:1",
                "Subject": "foo/bar",
                "Target": "cloud",
            }
        ]
    }
    subscription_name = "TestSubscription"
    client.create_subscription_definition(
        InitialVersion=init_ver, Name=subscription_name
    )

    res = client.list_subscription_definitions()
    res["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    subscription_def = res["Definitions"][0]
    subscription_def.should.have.key("Name").equals(subscription_name)
    subscription_def.should.have.key("Arn")
    subscription_def.should.have.key("Id")
    subscription_def.should.have.key("LatestVersion")
    subscription_def.should.have.key("LatestVersionArn")
    if not TEST_SERVER_MODE:
        subscription_def.should.have.key("CreationTimestamp").equal(
            "2022-06-01T12:00:00.000Z"
        )
        subscription_def.should.have.key("LastUpdatedTimestamp").equals(
            "2022-06-01T12:00:00.000Z"
        )


@freezegun.freeze_time("2022-06-01 12:00:00")
@mock_greengrass
def test_create_subscription_definition_version():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    v1_subscriptions = [
        {
            "Id": "123456",
            "Source": "cloud",
            "Subject": "foo/bar",
            "Target": "arn:aws:lambda:ap-northeast-1:123456789012:function:test_func:1",
        }
    ]

    initial_version = {"Subscriptions": v1_subscriptions}
    subscription_def_res = client.create_subscription_definition(
        InitialVersion=initial_version, Name="TestSubscription"
    )
    subscription_def_id = subscription_def_res["Id"]

    v2_subscriptions = [
        {
            "Id": "123456",
            "Source": "cloud",
            "Subject": "foo/bar",
            "Target": "arn:aws:lambda:ap-northeast-1:123456789012:function:test_func:2",
        }
    ]

    subscription_def_ver_res = client.create_subscription_definition_version(
        SubscriptionDefinitionId=subscription_def_id, Subscriptions=v2_subscriptions
    )
    subscription_def_ver_res.should.have.key("Arn")
    subscription_def_ver_res.should.have.key("CreationTimestamp")
    subscription_def_ver_res.should.have.key("Id").equals(subscription_def_id)
    subscription_def_ver_res.should.have.key("Version")

    if not TEST_SERVER_MODE:
        subscription_def_ver_res["CreationTimestamp"].should.equal(
            "2022-06-01T12:00:00.000Z"
        )


@mock_greengrass
def test_create_subscription_definition_version_with_invalid_id():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    subscriptions = [
        {
            "Id": "123456",
            "Source": "cloud",
            "Subject": "foo/bar",
            "Target": "arn:aws:lambda:ap-northeast-1:123456789012:function:test_func:2",
        }
    ]

    with pytest.raises(ClientError) as ex:
        client.create_subscription_definition_version(
            SubscriptionDefinitionId="7b0bdeae-54c7-47cf-9f93-561e672efd9c",
            Subscriptions=subscriptions,
        )
    ex.value.response["Error"]["Message"].should.equal(
        "That subscriptions does not exist."
    )
    ex.value.response["Error"]["Code"].should.equal("IdNotFoundException")


@mock_greengrass
def test_create_subscription_definition_version_with_invalid_target():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    v1_subscriptions = [
        {
            "Id": "123456",
            "Source": "cloud",
            "Subject": "foo/bar",
            "Target": "arn:aws:lambda:ap-northeast-1:123456789012:function:test_func:1",
        }
    ]

    initial_version = {"Subscriptions": v1_subscriptions}
    subscription_def_res = client.create_subscription_definition(
        InitialVersion=initial_version, Name="TestSubscription"
    )
    subscription_def_id = subscription_def_res["Id"]

    v2_subscriptions = [
        {
            "Id": "999999",
            "Source": "cloud",
            "Subject": "foo/bar",
            "Target": "foo",
        }
    ]

    with pytest.raises(ClientError) as ex:
        client.create_subscription_definition_version(
            SubscriptionDefinitionId=subscription_def_id, Subscriptions=v2_subscriptions
        )

    ex.value.response["Error"]["Message"].should.equal(
        "The subscriptions definition is invalid or corrupted. (ErrorDetails: [Subscription target is invalid. ID is '999999' and Target is 'foo'])"
    )
    ex.value.response["Error"]["Code"].should.equal("400")


@mock_greengrass
def test_create_subscription_definition_version_with_invalid_source():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    v1_subscriptions = [
        {
            "Id": "123456",
            "Source": "cloud",
            "Subject": "foo/bar",
            "Target": "arn:aws:lambda:ap-northeast-1:123456789012:function:test_func:1",
        }
    ]

    initial_version = {"Subscriptions": v1_subscriptions}
    subscription_def_res = client.create_subscription_definition(
        InitialVersion=initial_version, Name="TestSubscription"
    )
    subscription_def_id = subscription_def_res["Id"]

    v2_subscriptions = [
        {
            "Id": "999999",
            "Source": "foo",
            "Subject": "foo/bar",
            "Target": "arn:aws:lambda:ap-northeast-1:123456789012:function:test_func:1",
        }
    ]

    with pytest.raises(ClientError) as ex:
        client.create_subscription_definition_version(
            SubscriptionDefinitionId=subscription_def_id, Subscriptions=v2_subscriptions
        )

    ex.value.response["Error"]["Message"].should.equal(
        "The subscriptions definition is invalid or corrupted. (ErrorDetails: [Subscription source is invalid. ID is '999999' and Source is 'foo'])"
    )
    ex.value.response["Error"]["Code"].should.equal("400")
