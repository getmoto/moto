import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import

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

    resp.should.have.key("Users").equals([{"Username": "admin"}])


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

    resp.should.have.key("BrokerId").equals(broker_id)
    resp.should.have.key("ConsoleAccess").equals(True)
    resp.should.have.key("Groups").equals(["group1", "group2"])
    resp.should.have.key("Username").equals("admin")


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
    err["Code"].should.equal("NotFoundException")
    err["Message"].should.equal(
        "Can't find requested user [unknown]. Make sure your user exists."
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

    resp.should.have.key("BrokerId").equals(broker_id)
    resp.should.have.key("Users").equals([])


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

    resp.should.have.key("BrokerId").equals(broker_id)
    resp.should.have.key("Users").length_of(2)
    resp["Users"].should.contain({"Username": "admin"})
    resp["Users"].should.contain({"Username": "user1"})


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

    resp.should.have.key("BrokerId").equals(broker_id)
    resp.should.have.key("Groups").equals(["administrators"])
    resp.should.have.key("Username").equals("admin")


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

    resp.should.have.key("BrokerId").equals(broker_id)
    resp.should.have.key("Users").length_of(1)
    resp["Users"].should.contain({"Username": "user1"})
