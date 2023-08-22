import boto3

from moto import mock_mq


@mock_mq
def test_create_broker_with_tags():
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
def test_create_tags():
    client = boto3.client("mq", region_name="us-east-2")
    resp = client.create_broker(
        AutoMinorVersionUpgrade=False,
        BrokerName="testbroker",
        DeploymentMode="CLUSTER_MULTI_AZ",
        EngineType="RabbitMQ",
        EngineVersion="version",
        HostInstanceType="hit",
        PubliclyAccessible=True,
        Users=[],
    )

    broker_arn = resp["BrokerArn"]
    broker_id = resp["BrokerId"]

    client.create_tags(ResourceArn=broker_arn, Tags={"key1": "val2", "key2": "val2"})

    resp = client.describe_broker(BrokerId=broker_id)

    assert resp["Tags"] == {"key1": "val2", "key2": "val2"}

    tags = client.list_tags(ResourceArn=broker_arn)["Tags"]
    assert tags == {"key1": "val2", "key2": "val2"}


@mock_mq
def test_delete_tags():
    client = boto3.client("mq", region_name="us-east-2")
    resp = client.create_broker(
        AutoMinorVersionUpgrade=False,
        BrokerName="testbroker",
        DeploymentMode="CLUSTER_MULTI_AZ",
        EngineType="RabbitMQ",
        EngineVersion="version",
        HostInstanceType="hit",
        PubliclyAccessible=True,
        Users=[],
    )

    broker_arn = resp["BrokerArn"]
    broker_id = resp["BrokerId"]

    client.create_tags(ResourceArn=broker_arn, Tags={"key1": "val2", "key2": "val2"})

    client.delete_tags(ResourceArn=broker_arn, TagKeys=["key1"])

    resp = client.describe_broker(BrokerId=broker_id)

    assert resp["Tags"] == {"key2": "val2"}


@mock_mq
def test_create_configuration_with_tags():
    client = boto3.client("mq", region_name="ap-southeast-1")
    resp = client.create_configuration(
        EngineType="ACTIVEMQ",
        EngineVersion="rabbit1",
        Name="myconfig",
        Tags={"key1": "val1", "key2": "val2"},
    )

    # The CreateConfiguration call does not return tags
    assert "Tags" not in resp

    # Only when describing will they be returned
    resp = client.describe_configuration(ConfigurationId=resp["Id"])
    assert resp["Tags"] == {"key1": "val1", "key2": "val2"}


@mock_mq
def test_add_tags_to_configuration():
    client = boto3.client("mq", region_name="ap-southeast-1")
    resp = client.create_configuration(
        EngineType="ACTIVEMQ",
        EngineVersion="rabbit1",
        Name="myconfig",
        Tags={"key1": "val1", "key2": "val2"},
    )

    client.create_tags(ResourceArn=resp["Arn"], Tags={"key1": "val1", "key2": "val2"})

    # Only when describing will they be returned
    resp = client.describe_configuration(ConfigurationId=resp["Id"])
    assert resp["Tags"] == {"key1": "val1", "key2": "val2"}
