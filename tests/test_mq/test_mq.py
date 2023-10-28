import boto3
import pytest

from botocore.exceptions import ClientError
from moto import mock_mq

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_mq
def test_create_broker_minimal():
    client = boto3.client("mq", region_name="ap-southeast-1")
    resp = client.create_broker(
        AutoMinorVersionUpgrade=False,
        BrokerName="testbroker",
        DeploymentMode="dm",
        EngineType="ACTIVEMQ",
        EngineVersion="version",
        HostInstanceType="hit",
        PubliclyAccessible=True,
        Users=[{"Username": "admin", "Password": "adm1n"}],
    )

    assert "BrokerId" in resp
    assert resp["BrokerArn"].startswith("arn:aws")

    # Should create default Configuration, if not specified
    broker = client.describe_broker(BrokerId=resp["BrokerId"])
    assert "Current" in broker["Configurations"]
    assert "Id" in broker["Configurations"]["Current"]


@mock_mq
def test_create_with_tags():
    client = boto3.client("mq", region_name="us-east-2")
    broker_id = client.create_broker(
        AutoMinorVersionUpgrade=False,
        BrokerName="testbroker",
        DeploymentMode="CLUSTER_MULTI_AZ",
        EngineType="RabbitMQ",
        EngineVersion="version",
        HostInstanceType="hit",
        PubliclyAccessible=True,
        Tags={"key1": "val2", "key2": "val2"},
        Users=[],
    )["BrokerId"]

    resp = client.describe_broker(BrokerId=broker_id)

    assert resp["Tags"] == {"key1": "val2", "key2": "val2"}


@mock_mq
def test_create_with_multiple_users():
    client = boto3.client("mq", region_name="us-east-2")
    broker_id = client.create_broker(
        AutoMinorVersionUpgrade=False,
        BrokerName="testbroker",
        DeploymentMode="CLUSTER_MULTI_AZ",
        EngineType="RabbitMQ",
        EngineVersion="version",
        HostInstanceType="hit",
        PubliclyAccessible=True,
        Users=[
            {
                "ConsoleAccess": True,
                "Groups": ["second", "first", "third"],
                "Password": "SecondTestTest1234",
                "Username": "SecondTest",
            },
            {
                "ConsoleAccess": False,
                "Groups": [],
                "Password": "TestTest1234",
                "Username": "Test",
            },
        ],
    )["BrokerId"]

    user1 = client.describe_user(BrokerId=broker_id, Username="SecondTest")
    assert user1["Username"] == "SecondTest"
    assert user1["Groups"] == ["second", "first", "third"]
    assert user1["ConsoleAccess"] is True

    user2 = client.describe_user(BrokerId=broker_id, Username="Test")
    assert user2["Username"] == "Test"
    assert user2["Groups"] == []
    assert user2["ConsoleAccess"] is False


@mock_mq
def test_create_with_configuration():
    client = boto3.client("mq", region_name="us-east-2")
    broker_id = client.create_broker(
        AutoMinorVersionUpgrade=False,
        BrokerName="testbroker",
        Configuration={"Id": "config_id_x", "Revision": 3},
        DeploymentMode="CLUSTER_SINGLE",
        EngineType="ActiveMQ",
        EngineVersion="version",
        HostInstanceType="hit",
        PubliclyAccessible=True,
        Tags={"key1": "val2", "key2": "val2"},
        Users=[],
    )["BrokerId"]

    resp = client.describe_broker(BrokerId=broker_id)

    assert "Configurations" in resp
    assert resp["Configurations"]["Current"] == {"Id": "config_id_x", "Revision": 3}


@mock_mq
def test_update_with_configuration():
    client = boto3.client("mq", region_name="us-east-2")
    broker_id = client.create_broker(
        AutoMinorVersionUpgrade=False,
        BrokerName="testbroker",
        Configuration={"Id": "config_id_x", "Revision": 1},
        DeploymentMode="CLUSTER_SINGLE",
        EngineType="ActiveMQ",
        EngineVersion="version",
        HostInstanceType="hit",
        PubliclyAccessible=True,
        Tags={"key1": "val2", "key2": "val2"},
        Users=[],
    )["BrokerId"]

    client.update_broker(
        BrokerId=broker_id, Configuration={"Id": "config_id_x", "Revision": 2}
    )

    resp = client.describe_broker(BrokerId=broker_id)

    assert "Configurations" in resp
    assert resp["Configurations"]["Current"] == {"Id": "config_id_x", "Revision": 2}


@mock_mq
def test_delete_broker():
    client = boto3.client("mq", region_name="ap-southeast-1")
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

    resp = client.delete_broker(BrokerId=broker_id)
    assert resp["BrokerId"] == broker_id

    assert len(client.list_brokers()["BrokerSummaries"]) == 0


@mock_mq
def test_describe_broker():
    client = boto3.client("mq", region_name="us-east-2")
    broker_id = client.create_broker(
        AuthenticationStrategy="SIMPLE",
        AutoMinorVersionUpgrade=False,
        BrokerName="testbroker",
        DeploymentMode="dm",
        EncryptionOptions={"KmsKeyId": "kms-key", "UseAwsOwnedKey": False},
        EngineType="ACTIVEMQ",
        EngineVersion="version",
        LdapServerMetadata={
            "Hosts": ["host1"],
            "RoleBase": "role_base_thingy",
            "RoleSearchMatching": "rsm",
            "ServiceAccountUsername": "sau",
            "ServiceAccountPassword": "sap",
            "UserBase": "ub",
            "UserSearchMatching": "usm",
        },
        HostInstanceType="hit",
        PubliclyAccessible=True,
        SecurityGroups=["secgroup1"],
        StorageType="efs",
        SubnetIds=["s-id"],
        Users=[{"Username": "admin", "Password": "adm1n"}],
    )["BrokerId"]

    resp = client.describe_broker(BrokerId=broker_id)

    assert resp["BrokerId"] == broker_id
    assert resp["BrokerArn"].startswith("arn:aws")
    assert resp["BrokerState"] == "RUNNING"

    assert "Created" in resp

    assert resp["AuthenticationStrategy"] == "SIMPLE"
    assert resp["AutoMinorVersionUpgrade"] is False
    assert resp["BrokerName"] == "testbroker"
    assert resp["DeploymentMode"] == "dm"
    assert resp["EncryptionOptions"] == {"KmsKeyId": "kms-key", "UseAwsOwnedKey": False}
    assert resp["EngineType"] == "ACTIVEMQ"
    assert resp["EngineVersion"] == "version"
    assert resp["HostInstanceType"] == "hit"
    assert resp["LdapServerMetadata"] == {
        "Hosts": ["host1"],
        "RoleBase": "role_base_thingy",
        "RoleSearchMatching": "rsm",
        "ServiceAccountUsername": "sau",
        "UserBase": "ub",
        "UserSearchMatching": "usm",
    }
    assert resp["PubliclyAccessible"] is True
    assert resp["SecurityGroups"] == ["secgroup1"]
    assert resp["StorageType"] == "efs"
    assert resp["SubnetIds"] == ["s-id"]
    assert resp["Users"] == [{"Username": "admin"}]


@mock_mq
def test_describe_broker_with_defaults():
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

    resp = client.describe_broker(BrokerId=broker_id)

    assert len(resp["BrokerInstances"]) == 1

    assert "Configurations" in resp
    assert "Current" in resp["Configurations"]
    assert len(resp["Configurations"]["History"]) == 0
    assert "Pending" not in resp["Configurations"]

    assert resp["EncryptionOptions"] == {"UseAwsOwnedKey": True}

    assert resp["MaintenanceWindowStartTime"] == {
        "DayOfWeek": "Sunday",
        "TimeOfDay": "00:00",
        "TimeZone": "UTC",
    }

    assert resp["Logs"] == {"Audit": False, "General": False}

    assert len(resp["SubnetIds"]) == 1


@mock_mq
def test_describe_multiple_rabbits():
    client = boto3.client("mq", region_name="us-east-2")
    broker_id = client.create_broker(
        AutoMinorVersionUpgrade=False,
        BrokerName="testbroker",
        DeploymentMode="CLUSTER_MULTI_AZ",
        EngineType="RabbitMQ",
        EngineVersion="version",
        HostInstanceType="hit",
        PubliclyAccessible=True,
        Users=[],
    )["BrokerId"]

    resp = client.describe_broker(BrokerId=broker_id)

    assert "BrokerInstances" in resp
    assert (
        resp["BrokerInstances"][0]["ConsoleURL"]
        == "https://0000.mq.us-east-2.amazonaws.com"
    )
    assert len(resp["BrokerInstances"][0]["Endpoints"]) == 1
    assert resp["Logs"] == {"General": False}
    assert len(resp["SubnetIds"]) == 4


@mock_mq
def test_describe_active_mq_with_standby():
    client = boto3.client("mq", region_name="us-east-2")
    broker_id = client.create_broker(
        AutoMinorVersionUpgrade=False,
        BrokerName="testbroker",
        DeploymentMode="ACTIVE_STANDBY_MULTI_AZ",
        EngineType="ActiveMQ",
        EngineVersion="version",
        HostInstanceType="hit",
        PubliclyAccessible=True,
        Users=[],
    )["BrokerId"]

    resp = client.describe_broker(BrokerId=broker_id)

    # Instances and subnets in two regions - one active, one standby
    assert len(resp["BrokerInstances"]) == 2
    assert len(resp["SubnetIds"]) == 2


@mock_mq
def test_describe_broker_unknown():
    client = boto3.client("mq", region_name="us-east-2")

    with pytest.raises(ClientError) as exc:
        client.describe_broker(BrokerId="unknown")
    err = exc.value.response["Error"]
    assert err["Code"] == "NotFoundException"
    assert (
        err["Message"]
        == "Can't find requested broker [unknown]. Make sure your broker exists."
    )


@mock_mq
def test_list_brokers_empty():
    client = boto3.client("mq", region_name="eu-west-1")
    resp = client.list_brokers()

    assert resp["BrokerSummaries"] == []


@mock_mq
def test_list_brokers():
    client = boto3.client("mq", region_name="eu-west-1")
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

    resp = client.list_brokers()

    assert len(resp["BrokerSummaries"]) == 1

    summary = resp["BrokerSummaries"][0]
    assert "BrokerArn" in summary
    assert summary["BrokerId"] == broker_id
    assert summary["BrokerName"] == "testbroker"
    assert summary["BrokerState"] == "RUNNING"
    assert "Created" in summary
    assert summary["DeploymentMode"] == "dm"
    assert summary["EngineType"] == "ACTIVEMQ"
    assert summary["HostInstanceType"] == "hit"

    assert "Users" not in summary


@mock_mq
def test_update_broker_single_attribute():
    client = boto3.client("mq", region_name="ap-southeast-1")
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
    resp = client.update_broker(AutoMinorVersionUpgrade=True, BrokerId=broker_id)

    # Changed
    assert resp["AutoMinorVersionUpgrade"] is True

    # Unchanged
    assert resp["BrokerId"] == broker_id
    assert resp["EngineVersion"] == "version"


@mock_mq
def test_update_broker_multiple_attributes():
    client = boto3.client("mq", region_name="ap-southeast-1")
    broker_id = client.create_broker(
        AutoMinorVersionUpgrade=False,
        BrokerName="testbroker",
        DeploymentMode="dm",
        EngineType="ACTIVEMQ",
        EngineVersion="version",
        HostInstanceType="hit",
        PubliclyAccessible=True,
        SecurityGroups=["sg-1"],
        Users=[{"Username": "admin", "Password": "adm1n"}],
    )["BrokerId"]
    resp = client.update_broker(
        AutoMinorVersionUpgrade=True,
        BrokerId=broker_id,
        Logs={"Audit": True, "General": True},
        EngineVersion="version2",
        SecurityGroups=["sg-1", "sg-2"],
    )

    # Changed
    assert resp["AutoMinorVersionUpgrade"] is True
    assert resp["Logs"] == {"Audit": True, "General": True}
    assert resp["EngineVersion"] == "version2"
    assert resp["SecurityGroups"] == ["sg-1", "sg-2"]

    # Unchanged
    assert resp["BrokerId"] == broker_id


@mock_mq
def test_reboot_broker():
    client = boto3.client("mq", region_name="ap-southeast-1")
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
    client.reboot_broker(BrokerId=broker_id)

    # Noop - nothing to assert or verify
    pass
