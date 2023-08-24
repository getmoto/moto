import boto3
import pytest

from botocore.exceptions import ClientError
from moto import mock_mq


@mock_mq
def test_create_user():
    client = boto3.client("mq", region_name="us-east-1")
    broker_id = client.create_broker(
        AutoMinorVersionUpgrade=False,
        BrokerName="testbroker",
        DeploymentMode="dm",
        EngineType="ACTIVEMQ",
        EngineVersion="version",
        HostInstanceType="hit",
        PubliclyAccessible=True,
        Users=[],
    )["BrokerId"]

    client.create_user(BrokerId=broker_id, Username="admin", Password="adm1n")

    resp = client.describe_broker(BrokerId=broker_id)

    assert resp["Users"] == [{"Username": "admin"}]


@mock_mq
def test_describe_user():
    client = boto3.client("mq", region_name="us-east-1")
    broker_id = client.create_broker(
        AutoMinorVersionUpgrade=False,
        BrokerName="testbroker",
        DeploymentMode="dm",
        EngineType="ACTIVEMQ",
        EngineVersion="version",
        HostInstanceType="hit",
        PubliclyAccessible=True,
        Users=[],
    )["BrokerId"]

    client.create_user(
        BrokerId=broker_id,
        Username="admin",
        Password="adm1n",
        ConsoleAccess=True,
        Groups=["group1", "group2"],
    )

    resp = client.describe_user(BrokerId=broker_id, Username="admin")

    assert resp["BrokerId"] == broker_id
    assert resp["ConsoleAccess"] is True
    assert resp["Groups"] == ["group1", "group2"]
    assert resp["Username"] == "admin"


@mock_mq
def test_describe_user_unknown():
    client = boto3.client("mq", region_name="us-east-2")
    broker_id = client.create_broker(
        AutoMinorVersionUpgrade=False,
        BrokerName="testbroker",
        DeploymentMode="dm",
        EngineType="ACTIVEMQ",
        EngineVersion="version",
        HostInstanceType="hit",
        PubliclyAccessible=True,
        Users=[],
    )["BrokerId"]

    with pytest.raises(ClientError) as exc:
        client.describe_user(BrokerId=broker_id, Username="unknown")
    err = exc.value.response["Error"]
    assert err["Code"] == "NotFoundException"
    assert (
        err["Message"]
        == "Can't find requested user [unknown]. Make sure your user exists."
    )


@mock_mq
def test_list_users_empty():
    client = boto3.client("mq", region_name="us-east-1")
    broker_id = client.create_broker(
        AutoMinorVersionUpgrade=False,
        BrokerName="testbroker",
        DeploymentMode="dm",
        EngineType="ACTIVEMQ",
        EngineVersion="version",
        HostInstanceType="hit",
        PubliclyAccessible=True,
        Users=[],
    )["BrokerId"]

    resp = client.list_users(BrokerId=broker_id)

    assert resp["BrokerId"] == broker_id
    assert resp["Users"] == []


@mock_mq
def test_list_users():
    client = boto3.client("mq", region_name="us-east-1")
    broker_id = client.create_broker(
        AutoMinorVersionUpgrade=False,
        BrokerName="testbroker",
        DeploymentMode="dm",
        EngineType="ACTIVEMQ",
        EngineVersion="version",
        HostInstanceType="hit",
        PubliclyAccessible=True,
        Users=[{"Username": "admin", "Password": "adm1n"}],
    )["BrokerId"]

    client.create_user(BrokerId=broker_id, Username="user1", Password="us3r1")

    resp = client.list_users(BrokerId=broker_id)

    assert resp["BrokerId"] == broker_id
    assert len(resp["Users"]) == 2
    assert {"Username": "admin"} in resp["Users"]
    assert {"Username": "user1"} in resp["Users"]


@mock_mq
def test_update_user():
    client = boto3.client("mq", region_name="us-east-2")
    broker_id = client.create_broker(
        AutoMinorVersionUpgrade=False,
        BrokerName="testbroker",
        DeploymentMode="dm",
        EngineType="ACTIVEMQ",
        EngineVersion="version",
        HostInstanceType="hit",
        PubliclyAccessible=True,
        Users=[{"Username": "admin", "Password": "adm1n"}],
    )["BrokerId"]

    client.update_user(BrokerId=broker_id, Username="admin", Groups=["administrators"])

    resp = client.describe_user(BrokerId=broker_id, Username="admin")

    assert resp["BrokerId"] == broker_id
    assert resp["Groups"] == ["administrators"]
    assert resp["Username"] == "admin"


@mock_mq
def test_delete_user():
    client = boto3.client("mq", region_name="us-east-1")
    broker_id = client.create_broker(
        AutoMinorVersionUpgrade=False,
        BrokerName="testbroker",
        DeploymentMode="dm",
        EngineType="ACTIVEMQ",
        EngineVersion="version",
        HostInstanceType="hit",
        PubliclyAccessible=True,
        Users=[{"Username": "admin", "Password": "adm1n"}],
    )["BrokerId"]

    client.create_user(BrokerId=broker_id, Username="user1", Password="us3r1")

    client.delete_user(BrokerId=broker_id, Username="admin")

    resp = client.list_users(BrokerId=broker_id)

    assert resp["BrokerId"] == broker_id
    assert len(resp["Users"]) == 1
    assert {"Username": "user1"} in resp["Users"]
