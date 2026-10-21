import base64

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_aws
def test_create_configuration_minimal():
    client = boto3.client("mq", region_name="ap-southeast-1")
    resp = client.create_configuration(
        EngineType="ACTIVEMQ", EngineVersion="rabbit1", Name="myconfig"
    )

    assert resp["Id"].startswith("c-")
    assert (
        resp["Arn"]
        == f"arn:aws:mq:ap-southeast-1:{ACCOUNT_ID}:configuration:{resp['Id']}"
    )
    assert resp["AuthenticationStrategy"] == "simple"
    assert "Created" in resp
    assert resp["Name"] == "myconfig"
    assert "LatestRevision" in resp

    revision = resp["LatestRevision"]
    assert "Created" in revision
    assert "Description" in revision
    assert revision["Revision"] == 1


@mock_aws
def test_create_configuration_for_unknown_engine():
    client = boto3.client("mq", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        client.create_configuration(
            EngineType="unknown", EngineVersion="rabbit1", Name="myconfig"
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "BadRequestException"
    assert (
        err["Message"]
        == "Broker engine type [unknown] is invalid. Valid values are: [ACTIVEMQ]"
    )


@mock_aws
def test_describe_configuration():
    client = boto3.client("mq", region_name="eu-north-1")
    config_id = client.create_configuration(
        EngineType="ACTIVEMQ", EngineVersion="active2", Name="myconfig"
    )["Id"]

    resp = client.describe_configuration(ConfigurationId=config_id)

    assert resp["Id"].startswith("c-")
    assert (
        resp["Arn"] == f"arn:aws:mq:eu-north-1:{ACCOUNT_ID}:configuration:{resp['Id']}"
    )
    assert resp["AuthenticationStrategy"] == "simple"
    assert "Created" in resp
    assert resp["Name"] == "myconfig"
    assert "LatestRevision" in resp

    revision = resp["LatestRevision"]
    assert "Created" in revision
    assert "Description" in revision
    assert revision["Revision"] == 1


@mock_aws
def test_describe_configuration_revision():
    client = boto3.client("mq", region_name="eu-north-1")
    config_id = client.create_configuration(
        EngineType="ActiveMQ", EngineVersion="5.16.3", Name="myconfig"
    )["Id"]

    resp = client.describe_configuration_revision(
        ConfigurationId=config_id, ConfigurationRevision="1"
    )

    assert resp["ConfigurationId"] == config_id
    assert "Created" in resp
    assert (
        resp["Description"] == "Auto-generated default for myconfig on ActiveMQ 5.16.3"
    )

    assert "Data" in resp


@mock_aws
def test_describe_configuration_unknown():
    client = boto3.client("mq", region_name="us-east-2")

    with pytest.raises(ClientError) as exc:
        client.describe_configuration(ConfigurationId="c-unknown")
    err = exc.value.response["Error"]

    assert err["Code"] == "NotFoundException"
    assert (
        err["Message"]
        == "Can't find requested configuration [c-unknown]. Make sure your configuration exists."
    )


@mock_aws
def test_list_configurations_empty():
    client = boto3.client("mq", region_name="us-east-2")

    resp = client.list_configurations()

    assert resp["Configurations"] == []


@mock_aws
def test_list_configurations():
    client = boto3.client("mq", region_name="ap-southeast-1")
    config_id = client.create_configuration(
        EngineType="ACTIVEMQ", EngineVersion="active1", Name="myconfig"
    )["Id"]

    resp = client.list_configurations()

    assert len(resp["Configurations"]) == 1

    config = resp["Configurations"][0]
    assert config["Arn"].startswith("arn:aws")
    assert "Created" in config
    assert config["Id"] == config_id
    assert config["Name"] == "myconfig"
    assert config["EngineType"] == "ACTIVEMQ"
    assert config["EngineVersion"] == "active1"


@mock_aws
def test_update_configuration():
    client = boto3.client("mq", region_name="ap-southeast-1")
    config_id = client.create_configuration(
        EngineType="ACTIVEMQ", EngineVersion="rabbit1", Name="myconfig"
    )["Id"]

    resp = client.update_configuration(
        ConfigurationId=config_id,
        Data="base64encodedxmlconfig",
        Description="updated config",
    )

    assert resp["Arn"].startswith("arn:aws:mq")
    assert "Created" in resp
    assert "Id" in resp
    assert resp["Name"] == "myconfig"
    assert "LatestRevision" in resp

    revision = resp["LatestRevision"]
    assert "Created" in revision
    assert revision["Description"] == "updated config"
    assert revision["Revision"] == 2


@mock_aws
def test_update_configuration_to_ldap():
    client = boto3.client("mq", region_name="ap-southeast-1")
    config_id = client.create_configuration(
        EngineType="ACTIVEMQ", EngineVersion="rabbit1", Name="myconfig"
    )["Id"]

    ldap_config = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<broker xmlns="http://activemq.apache.org/schema/core">
  <plugins>
    <authorizationPlugin>
      <map>
        <cachedLDAPAuthorizationMap legacyGroupMapping="false" queueSearchBase="ou=Queue,ou=Destination,ou=ActiveMQ,dc=example,dc=org" refreshInterval="0" tempSearchBase="ou=Temp,ou=Destination,ou=ActiveMQ,dc=example,dc=org" topicSearchBase="ou=Topic,ou=Destination,ou=ActiveMQ,dc=example,dc=org"/>
      </map>
    </authorizationPlugin>
    <forcePersistencyModeBrokerPlugin persistenceFlag="true"/>
    <statisticsBrokerPlugin/>
    <timeStampingBrokerPlugin ttlCeiling="86400000" zeroExpirationOverride="86400000"/>
  </plugins>
</broker>
"""

    client.update_configuration(
        ConfigurationId=config_id,
        Data=base64.b64encode(ldap_config.encode("utf-8")).decode("utf-8"),
        Description="update config to use LDAP authorization",
    )

    resp = client.describe_configuration(ConfigurationId=config_id)

    assert resp["AuthenticationStrategy"] == "ldap"


@mock_aws
def test_list_configuration_revisions():
    client = boto3.client("mq", region_name="eu-west-1")
    config_id = client.create_configuration(
        EngineType="ActiveMQ", EngineVersion="5.16.3", Name="myconfig"
    )["Id"]
    client.update_configuration(
        ConfigurationId=config_id, Data="ZGF0YQ==", Description="second"
    )
    client.update_configuration(
        ConfigurationId=config_id, Data="ZGF0YQ==", Description="third"
    )

    resp = client.list_configuration_revisions(ConfigurationId=config_id)

    assert resp["ConfigurationId"] == config_id
    assert "NextToken" not in resp
    revisions = resp["Revisions"]
    assert [r["Revision"] for r in revisions] == [1, 2, 3]
    assert [r["Description"] for r in revisions] == [
        "Auto-generated default for myconfig on ActiveMQ 5.16.3",
        "second",
        "third",
    ]
    assert all("Created" in r for r in revisions)


@mock_aws
def test_list_configuration_revisions_pagination():
    client = boto3.client("mq", region_name="eu-west-1")
    config_id = client.create_configuration(
        EngineType="ACTIVEMQ", EngineVersion="5.16.3", Name="myconfig"
    )["Id"]
    for idx in range(2, 13):
        client.update_configuration(
            ConfigurationId=config_id, Data="ZGF0YQ==", Description=f"rev {idx}"
        )

    page1 = client.list_configuration_revisions(ConfigurationId=config_id, MaxResults=5)
    assert page1["MaxResults"] == 5
    assert [r["Revision"] for r in page1["Revisions"]] == [1, 2, 3, 4, 5]

    page2 = client.list_configuration_revisions(
        ConfigurationId=config_id, MaxResults=5, NextToken=page1["NextToken"]
    )
    assert [r["Revision"] for r in page2["Revisions"]] == [6, 7, 8, 9, 10]

    page3 = client.list_configuration_revisions(
        ConfigurationId=config_id, MaxResults=5, NextToken=page2["NextToken"]
    )
    assert [r["Revision"] for r in page3["Revisions"]] == [11, 12]
    assert page3["Revisions"][-1]["Description"] == "rev 12"
    assert "NextToken" not in page3

    latest = client.describe_configuration(ConfigurationId=config_id)
    assert latest["LatestRevision"]["Revision"] == 12
    assert latest["LatestRevision"]["Description"] == "rev 12"


@mock_aws
def test_list_configuration_revisions_unknown():
    client = boto3.client("mq", region_name="eu-west-1")

    with pytest.raises(ClientError) as exc:
        client.list_configuration_revisions(ConfigurationId="c-unknown")
    err = exc.value.response["Error"]

    assert err["Code"] == "NotFoundException"
    assert (
        err["Message"]
        == "Can't find requested configuration [c-unknown]. Make sure your configuration exists."
    )


@mock_aws
def test_delete_configuration():
    client = boto3.client("mq", region_name="us-west-2")
    config = client.create_configuration(
        EngineType="ACTIVEMQ",
        EngineVersion="5.16.3",
        Name="myconfig",
        Tags={"key": "value"},
    )
    config_id = config["Id"]

    resp = client.delete_configuration(ConfigurationId=config_id)
    assert resp["ConfigurationId"] == config_id

    assert client.list_configurations()["Configurations"] == []
    assert client.list_tags(ResourceArn=config["Arn"])["Tags"] == {}
    with pytest.raises(ClientError) as exc:
        client.describe_configuration(ConfigurationId=config_id)
    assert exc.value.response["Error"]["Code"] == "NotFoundException"


@mock_aws
def test_delete_configuration_unknown():
    client = boto3.client("mq", region_name="us-west-2")

    with pytest.raises(ClientError) as exc:
        client.delete_configuration(ConfigurationId="c-unknown")
    err = exc.value.response["Error"]

    assert err["Code"] == "NotFoundException"
    assert (
        err["Message"]
        == "Can't find requested configuration [c-unknown]. Make sure your configuration exists."
    )


@mock_aws
def test_delete_configuration_in_use_by_broker():
    client = boto3.client("mq", region_name="us-west-2")
    config_id = client.create_configuration(
        EngineType="ACTIVEMQ", EngineVersion="5.16.3", Name="myconfig"
    )["Id"]
    broker_id = client.create_broker(
        AutoMinorVersionUpgrade=False,
        BrokerName="testbroker",
        Configuration={"Id": config_id, "Revision": 1},
        DeploymentMode="SINGLE_INSTANCE",
        EngineType="ACTIVEMQ",
        EngineVersion="5.16.3",
        HostInstanceType="mq.t3.micro",
        PubliclyAccessible=True,
        Users=[],
    )["BrokerId"]

    with pytest.raises(ClientError) as exc:
        client.delete_configuration(ConfigurationId=config_id)
    err = exc.value.response["Error"]

    assert err["Code"] == "ConflictException"
    assert (
        err["Message"]
        == f"Configuration [{config_id}] is in use by broker [{broker_id}] and can't be deleted."
    )
    assert client.describe_configuration(ConfigurationId=config_id)["Id"] == config_id

    client.delete_broker(BrokerId=broker_id)
    client.delete_configuration(ConfigurationId=config_id)

    assert client.list_configurations()["Configurations"] == []
