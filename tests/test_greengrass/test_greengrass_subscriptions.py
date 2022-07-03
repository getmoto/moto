import boto3
from botocore.client import ClientError
import freezegun
import pytest

from moto import mock_greengrass
from moto.settings import TEST_SERVER_MODE


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
def test_get_subscription_definition():

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
    create_res = client.create_subscription_definition(
        InitialVersion=init_ver, Name=subscription_name
    )

    subscription_def_id = create_res["Id"]
    arn = create_res["Arn"]
    latest_version = create_res["LatestVersion"]
    latest_version_arn = create_res["LatestVersionArn"]

    get_res = client.get_subscription_definition(
        SubscriptionDefinitionId=subscription_def_id
    )

    get_res.should.have.key("Name").equals(subscription_name)
    get_res.should.have.key("Arn").equals(arn)
    get_res.should.have.key("Id").equals(subscription_def_id)
    get_res.should.have.key("LatestVersion").equals(latest_version)
    get_res.should.have.key("LatestVersionArn").equals(latest_version_arn)
    get_res["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    if not TEST_SERVER_MODE:
        get_res.should.have.key("CreationTimestamp").equal("2022-06-01T12:00:00.000Z")
        get_res.should.have.key("LastUpdatedTimestamp").equals(
            "2022-06-01T12:00:00.000Z"
        )


@mock_greengrass
def test_get_subscription_definition_with_invalid_id():

    client = boto3.client("greengrass", region_name="ap-northeast-1")
    with pytest.raises(ClientError) as ex:
        client.get_subscription_definition(
            SubscriptionDefinitionId="b552443b-1888-469b-81f8-0ebc5ca92949"
        )

    ex.value.response["Error"]["Message"].should.equal(
        "That Subscription List Definition does not exist."
    )
    ex.value.response["Error"]["Code"].should.equal("IdNotFoundException")


@mock_greengrass
def test_delete_subscription_definition():

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
    create_res = client.create_subscription_definition(
        InitialVersion=init_ver, Name="TestSubscription"
    )

    subscription_def_id = create_res["Id"]
    del_res = client.delete_subscription_definition(
        SubscriptionDefinitionId=subscription_def_id
    )
    del_res["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)


@mock_greengrass
def test_update_subscription_definition():

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
    create_res = client.create_subscription_definition(
        InitialVersion=init_ver, Name="TestSubscription"
    )

    subscription_def_id = create_res["Id"]
    updated_subscription_name = "UpdatedSubscription"
    update_res = client.update_subscription_definition(
        SubscriptionDefinitionId=subscription_def_id, Name=updated_subscription_name
    )
    update_res["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    get_res = client.get_subscription_definition(
        SubscriptionDefinitionId=subscription_def_id
    )
    get_res.should.have.key("Name").equals(updated_subscription_name)


@mock_greengrass
def test_update_subscription_definition_with_empty_name():

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
    create_res = client.create_subscription_definition(
        InitialVersion=init_ver, Name="TestSubscription"
    )
    subscription_def_id = create_res["Id"]

    with pytest.raises(ClientError) as ex:
        client.update_subscription_definition(
            SubscriptionDefinitionId=subscription_def_id, Name=""
        )
    ex.value.response["Error"]["Message"].should.equal(
        "Input does not contain any attributes to be updated"
    )
    ex.value.response["Error"]["Code"].should.equal(
        "InvalidContainerDefinitionException"
    )


@mock_greengrass
def test_update_subscription_definition_with_invalid_id():

    client = boto3.client("greengrass", region_name="ap-northeast-1")

    with pytest.raises(ClientError) as ex:
        client.update_subscription_definition(
            SubscriptionDefinitionId="6fbffc21-989e-4d29-a793-a42f450a78c6", Name="123"
        )
    ex.value.response["Error"]["Message"].should.equal(
        "That subscriptions definition does not exist."
    )
    ex.value.response["Error"]["Code"].should.equal("IdNotFoundException")


@mock_greengrass
def test_delete_subscription_definition_with_invalid_id():

    client = boto3.client("greengrass", region_name="ap-northeast-1")

    with pytest.raises(ClientError) as ex:
        client.delete_subscription_definition(
            SubscriptionDefinitionId="6fbffc21-989e-4d29-a793-a42f450a78c6"
        )
    ex.value.response["Error"]["Message"].should.equal(
        "That subscriptions definition does not exist."
    )
    ex.value.response["Error"]["Code"].should.equal("IdNotFoundException")


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


@freezegun.freeze_time("2022-06-01 12:00:00")
@mock_greengrass
def test_list_subscription_definition_versions():

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

    create_res = client.create_subscription_definition(
        InitialVersion=init_ver, Name="TestSubscription"
    )
    subscription_def_id = create_res["Id"]
    subscription_def_ver_res = client.list_subscription_definition_versions(
        SubscriptionDefinitionId=subscription_def_id
    )

    subscription_def_ver_res["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    subscription_def_ver_res.should.have.key("Versions")
    subscription_def_ver = subscription_def_ver_res["Versions"][0]
    subscription_def_ver.should.have.key("Arn")
    subscription_def_ver.should.have.key("CreationTimestamp")
    subscription_def_ver.should.have.key("Id").equals(subscription_def_id)
    subscription_def_ver.should.have.key("Version")

    if not TEST_SERVER_MODE:
        subscription_def_ver["CreationTimestamp"].should.equal(
            "2022-06-01T12:00:00.000Z"
        )


@mock_greengrass
def test_list_subscription_definition_versions_with_invalid_id():

    client = boto3.client("greengrass", region_name="ap-northeast-1")

    with pytest.raises(ClientError) as ex:
        client.list_subscription_definition_versions(
            SubscriptionDefinitionId="7b0bdeae-54c7-47cf-9f93-561e672efd9c"
        )
    ex.value.response["Error"]["Message"].should.equal(
        "That subscriptions definition does not exist."
    )
    ex.value.response["Error"]["Code"].should.equal("IdNotFoundException")


@freezegun.freeze_time("2022-06-01 12:00:00")
@mock_greengrass
def test_get_subscription_definition_version():

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
    create_res = client.create_subscription_definition(
        InitialVersion=init_ver, Name="TestSubscription"
    )

    subscription_def_id = create_res["Id"]
    subscription_def_ver_id = create_res["LatestVersion"]

    func_def_ver_res = client.get_subscription_definition_version(
        SubscriptionDefinitionId=subscription_def_id,
        SubscriptionDefinitionVersionId=subscription_def_ver_id,
    )

    func_def_ver_res.should.have.key("Arn")
    func_def_ver_res.should.have.key("CreationTimestamp")
    func_def_ver_res.should.have.key("Definition").should.equal(init_ver)
    func_def_ver_res.should.have.key("Id").equals(subscription_def_id)
    func_def_ver_res.should.have.key("Version")

    if not TEST_SERVER_MODE:
        func_def_ver_res["CreationTimestamp"].should.equal("2022-06-01T12:00:00.000Z")


@mock_greengrass
def test_get_subscription_definition_version_with_invalid_id():

    client = boto3.client("greengrass", region_name="ap-northeast-1")

    with pytest.raises(ClientError) as ex:
        client.get_subscription_definition_version(
            SubscriptionDefinitionId="7b0bdeae-54c7-47cf-9f93-561e672efd9c",
            SubscriptionDefinitionVersionId="7b0bdeae-54c7-47cf-9f93-561e672efd9c",
        )
    ex.value.response["Error"]["Message"].should.equal(
        "That subscriptions definition does not exist."
    )
    ex.value.response["Error"]["Code"].should.equal("IdNotFoundException")


@mock_greengrass
def test_get_subscription_definition_version_with_invalid_version_id():

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
    create_res = client.create_subscription_definition(
        InitialVersion=init_ver, Name="TestSubscription"
    )

    subscription_def_id = create_res["Id"]
    invalid_subscription_def_ver_id = "7b0bdeae-54c7-47cf-9f93-561e672efd9c"

    with pytest.raises(ClientError) as ex:
        client.get_subscription_definition_version(
            SubscriptionDefinitionId=subscription_def_id,
            SubscriptionDefinitionVersionId=invalid_subscription_def_ver_id,
        )
    ex.value.response["Error"]["Message"].should.equal(
        f"Version {invalid_subscription_def_ver_id} of Subscription List Definition {subscription_def_id} does not exist."
    )
    ex.value.response["Error"]["Code"].should.equal("VersionNotFoundException")
