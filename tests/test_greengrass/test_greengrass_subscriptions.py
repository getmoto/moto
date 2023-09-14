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
    assert "Arn" in res
    assert "Id" in res
    assert "LatestVersion" in res
    assert "LatestVersionArn" in res
    assert res["Name"] == subscription_name
    assert res["ResponseMetadata"]["HTTPStatusCode"] == 201

    if not TEST_SERVER_MODE:
        assert res["CreationTimestamp"] == "2022-06-01T12:00:00.000Z"
        assert res["LastUpdatedTimestamp"] == "2022-06-01T12:00:00.000Z"


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

    err = ex.value.response["Error"]
    assert (
        err["Message"]
        == "The subscriptions definition is invalid or corrupted. (ErrorDetails: [Subscription target is invalid. ID is '123456' and Target is 'foo'])"
    )
    assert err["Code"] == "400"


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

    err = ex.value.response["Error"]
    assert (
        err["Message"]
        == "The subscriptions definition is invalid or corrupted. (ErrorDetails: [Subscription source is invalid. ID is '123456' and Source is 'foo'])"
    )
    assert err["Code"] == "400"


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
    assert res["ResponseMetadata"]["HTTPStatusCode"] == 200

    subscription_def = res["Definitions"][0]
    assert subscription_def["Name"] == subscription_name
    assert "Arn" in subscription_def
    assert "Id" in subscription_def
    assert "LatestVersion" in subscription_def
    assert "LatestVersionArn" in subscription_def
    if not TEST_SERVER_MODE:
        assert subscription_def["CreationTimestamp"] == "2022-06-01T12:00:00.000Z"
        assert subscription_def["LastUpdatedTimestamp"] == "2022-06-01T12:00:00.000Z"


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

    assert get_res["Name"] == subscription_name
    assert get_res["Arn"] == arn
    assert get_res["Id"] == subscription_def_id
    assert get_res["LatestVersion"] == latest_version
    assert get_res["LatestVersionArn"] == latest_version_arn
    assert get_res["ResponseMetadata"]["HTTPStatusCode"] == 200

    if not TEST_SERVER_MODE:
        assert get_res["CreationTimestamp"] == "2022-06-01T12:00:00.000Z"
        assert get_res["LastUpdatedTimestamp"] == "2022-06-01T12:00:00.000Z"


@mock_greengrass
def test_get_subscription_definition_with_invalid_id():
    client = boto3.client("greengrass", region_name="ap-northeast-1")
    with pytest.raises(ClientError) as ex:
        client.get_subscription_definition(
            SubscriptionDefinitionId="b552443b-1888-469b-81f8-0ebc5ca92949"
        )

    err = ex.value.response["Error"]
    assert err["Message"] == "That Subscription List Definition does not exist."
    assert err["Code"] == "IdNotFoundException"


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
    assert del_res["ResponseMetadata"]["HTTPStatusCode"] == 200


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
    assert update_res["ResponseMetadata"]["HTTPStatusCode"] == 200

    get_res = client.get_subscription_definition(
        SubscriptionDefinitionId=subscription_def_id
    )
    assert get_res["Name"] == updated_subscription_name


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
    err = ex.value.response["Error"]
    assert err["Message"] == "Input does not contain any attributes to be updated"
    assert err["Code"] == "InvalidContainerDefinitionException"


@mock_greengrass
def test_update_subscription_definition_with_invalid_id():
    client = boto3.client("greengrass", region_name="ap-northeast-1")

    with pytest.raises(ClientError) as ex:
        client.update_subscription_definition(
            SubscriptionDefinitionId="6fbffc21-989e-4d29-a793-a42f450a78c6", Name="123"
        )
    err = ex.value.response["Error"]
    assert err["Message"] == "That subscriptions definition does not exist."
    assert err["Code"] == "IdNotFoundException"


@mock_greengrass
def test_delete_subscription_definition_with_invalid_id():
    client = boto3.client("greengrass", region_name="ap-northeast-1")

    with pytest.raises(ClientError) as ex:
        client.delete_subscription_definition(
            SubscriptionDefinitionId="6fbffc21-989e-4d29-a793-a42f450a78c6"
        )
    err = ex.value.response["Error"]
    assert err["Message"] == "That subscriptions definition does not exist."
    assert err["Code"] == "IdNotFoundException"


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
    assert "Arn" in subscription_def_ver_res
    assert "CreationTimestamp" in subscription_def_ver_res
    assert subscription_def_ver_res["Id"] == subscription_def_id
    assert "Version" in subscription_def_ver_res

    if not TEST_SERVER_MODE:
        assert (
            subscription_def_ver_res["CreationTimestamp"] == "2022-06-01T12:00:00.000Z"
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
    err = ex.value.response["Error"]
    assert err["Message"] == "That subscriptions does not exist."
    assert err["Code"] == "IdNotFoundException"


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

    err = ex.value.response["Error"]
    assert (
        err["Message"]
        == "The subscriptions definition is invalid or corrupted. (ErrorDetails: [Subscription target is invalid. ID is '999999' and Target is 'foo'])"
    )
    assert err["Code"] == "400"


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

    err = ex.value.response["Error"]
    assert (
        err["Message"]
        == "The subscriptions definition is invalid or corrupted. (ErrorDetails: [Subscription source is invalid. ID is '999999' and Source is 'foo'])"
    )
    assert err["Code"] == "400"


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

    assert subscription_def_ver_res["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert "Versions" in subscription_def_ver_res
    subscription_def_ver = subscription_def_ver_res["Versions"][0]
    assert "Arn" in subscription_def_ver
    assert "CreationTimestamp" in subscription_def_ver
    assert subscription_def_ver["Id"] == subscription_def_id
    assert "Version" in subscription_def_ver

    if not TEST_SERVER_MODE:
        assert subscription_def_ver["CreationTimestamp"] == "2022-06-01T12:00:00.000Z"


@mock_greengrass
def test_list_subscription_definition_versions_with_invalid_id():
    client = boto3.client("greengrass", region_name="ap-northeast-1")

    with pytest.raises(ClientError) as ex:
        client.list_subscription_definition_versions(
            SubscriptionDefinitionId="7b0bdeae-54c7-47cf-9f93-561e672efd9c"
        )
    err = ex.value.response["Error"]
    assert err["Message"] == "That subscriptions definition does not exist."
    assert err["Code"] == "IdNotFoundException"


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

    assert "Arn" in func_def_ver_res
    assert "CreationTimestamp" in func_def_ver_res
    assert func_def_ver_res["Definition"] == init_ver
    assert func_def_ver_res["Id"] == subscription_def_id
    assert "Version" in func_def_ver_res

    if not TEST_SERVER_MODE:
        assert func_def_ver_res["CreationTimestamp"] == "2022-06-01T12:00:00.000Z"


@mock_greengrass
def test_get_subscription_definition_version_with_invalid_id():
    client = boto3.client("greengrass", region_name="ap-northeast-1")

    with pytest.raises(ClientError) as ex:
        client.get_subscription_definition_version(
            SubscriptionDefinitionId="7b0bdeae-54c7-47cf-9f93-561e672efd9c",
            SubscriptionDefinitionVersionId="7b0bdeae-54c7-47cf-9f93-561e672efd9c",
        )
    err = ex.value.response["Error"]
    assert err["Message"] == "That subscriptions definition does not exist."
    assert err["Code"] == "IdNotFoundException"


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
    err = ex.value.response["Error"]
    assert (
        err["Message"]
        == f"Version {invalid_subscription_def_ver_id} of Subscription List Definition {subscription_def_id} does not exist."
    )
    assert err["Code"] == "VersionNotFoundException"
