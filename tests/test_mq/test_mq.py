import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import

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

    resp.should.have.key("BrokerId")
    resp.should.have.key("BrokerArn").match("arn:aws")


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

    resp.should.have.key("Tags").equals({"key1": "val2", "key2": "val2"})


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
    user1.should.have.key("Username").equals("SecondTest")
    user1.should.have.key("Groups").equals(["second", "first", "third"])
    user1.should.have.key("ConsoleAccess").equals(True)

    user2 = client.describe_user(BrokerId=broker_id, Username="Test")
    user2.should.have.key("Username").equals("Test")
    user2.should.have.key("Groups").equals([])
    user2.should.have.key("ConsoleAccess").equals(False)


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

    resp.should.have.key("Configurations")
    resp["Configurations"].should.have.key("Current").equals(
        {"Id": "config_id_x", "Revision": 3}
    )


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

    resp.should.have.key("Configurations")
    resp["Configurations"].should.have.key("Current").equals(
        {"Id": "config_id_x", "Revision": 2}
    )


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
    resp.should.have.key("BrokerId").equals(broker_id)

    client.list_brokers().should.have.key("BrokerSummaries").length_of(0)


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

    resp.should.have.key("BrokerId").equals(broker_id)
    resp.should.have.key("BrokerArn").match("arn:aws")
    resp.should.have.key("BrokerState").equals("RUNNING")

    resp.should.have.key("Created")

    resp.should.have.key("AuthenticationStrategy").equals("SIMPLE")
    resp.should.have.key("AutoMinorVersionUpgrade").equals(False)
    resp.should.have.key("BrokerName").equals("testbroker")
    resp.should.have.key("DeploymentMode").equals("dm")
    resp.should.have.key("EncryptionOptions").equals(
        {"KmsKeyId": "kms-key", "UseAwsOwnedKey": False}
    )
    resp.should.have.key("EngineType").equals("ACTIVEMQ")
    resp.should.have.key("EngineVersion").equals("version")
    resp.should.have.key("HostInstanceType").equals("hit")
    resp.should.have.key("LdapServerMetadata").equals(
        {
            "Hosts": ["host1"],
            "RoleBase": "role_base_thingy",
            "RoleSearchMatching": "rsm",
            "ServiceAccountUsername": "sau",
            "UserBase": "ub",
            "UserSearchMatching": "usm",
        }
    )
    resp.should.have.key("PubliclyAccessible").equals(True)
    resp.should.have.key("SecurityGroups").equals(["secgroup1"])
    resp.should.have.key("StorageType").equals("efs")
    resp.should.have.key("SubnetIds").equals(["s-id"])
    resp.should.have.key("Users").equals([{"Username": "admin"}])


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

    resp.should.have.key("BrokerInstances").length_of(1)

    resp.should.have.key("Configurations")
    resp["Configurations"].should.have.key("Current")
    resp["Configurations"].should.have.key("History").length_of(0)
    resp["Configurations"].shouldnt.have.key("Pending")

    resp.should.have.key("EncryptionOptions").equals({"UseAwsOwnedKey": True})

    resp.should.have.key("MaintenanceWindowStartTime").equals(
        {"DayOfWeek": "Sunday", "TimeOfDay": "00:00", "TimeZone": "UTC"}
    )

    resp.should.have.key("Logs").equals({"Audit": False, "General": False})

    resp.should.have.key("SubnetIds").length_of(1)


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

    resp.should.have.key("BrokerInstances")
    resp["BrokerInstances"][0]["ConsoleURL"].should.equal(
        "https://0000.mq.us-east-2.amazonaws.com"
    )
    resp["BrokerInstances"][0]["Endpoints"].should.have.length_of(1)
    resp.shouldnt.have.key("Configurations")
    resp.should.have.key("Logs").equals({"General": False})
    resp.should.have.key("SubnetIds").length_of(4)


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
    resp.should.have.key("BrokerInstances").length_of(2)
    resp.should.have.key("SubnetIds").length_of(2)


@mock_mq
def test_describe_broker_unknown():
    client = boto3.client("mq", region_name="us-east-2")

    with pytest.raises(ClientError) as exc:
        client.describe_broker(BrokerId="unknown")
    err = exc.value.response["Error"]
    err["Code"].should.equal("NotFoundException")
    err["Message"].should.equal(
        "Can't find requested broker [unknown]. Make sure your broker exists."
    )


@mock_mq
def test_list_brokers_empty():
    client = boto3.client("mq", region_name="eu-west-1")
    resp = client.list_brokers()

    resp.should.have.key("BrokerSummaries").equals([])


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

    resp.should.have.key("BrokerSummaries").length_of(1)

    summary = resp["BrokerSummaries"][0]
    summary.should.have.key("BrokerArn")
    summary.should.have.key("BrokerId").equals(broker_id)
    summary.should.have.key("BrokerName").equals("testbroker")
    summary.should.have.key("BrokerState").equals("RUNNING")
    summary.should.have.key("Created")
    summary.should.have.key("DeploymentMode").equals("dm")
    summary.should.have.key("EngineType").equals("ACTIVEMQ")
    summary.should.have.key("HostInstanceType").equals("hit")

    summary.shouldnt.have.key("Users")


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
    resp.should.have.key("AutoMinorVersionUpgrade").equals(True)

    # Unchanged
    resp.should.have.key("BrokerId").equals(broker_id)
    resp.should.have.key("EngineVersion").equals("version")


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
    resp.should.have.key("AutoMinorVersionUpgrade").equals(True)
    resp.should.have.key("Logs").equals({"Audit": True, "General": True})
    resp.should.have.key("EngineVersion").equals("version2")
    resp.should.have.key("SecurityGroups").equals(["sg-1", "sg-2"])

    # Unchanged
    resp.should.have.key("BrokerId").equals(broker_id)


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
