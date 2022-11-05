"""Unit tests for mq-supported APIs."""
import base64

import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import

from botocore.exceptions import ClientError
from moto import mock_mq
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_mq
def test_create_configuration_minimal():
    client = boto3.client("mq", region_name="ap-southeast-1")
    resp = client.create_configuration(
        EngineType="ACTIVEMQ", EngineVersion="rabbit1", Name="myconfig"
    )

    resp.should.have.key("Id").match("^c-")
    resp.should.have.key("Arn").equals(
        f"arn:aws:mq:ap-southeast-1:{ACCOUNT_ID}:configuration:{resp['Id']}"
    )
    resp.should.have.key("AuthenticationStrategy").equals("simple")
    resp.should.have.key("Created")
    resp.should.have.key("Name").equals("myconfig")
    resp.should.have.key("LatestRevision")

    revision = resp["LatestRevision"]
    revision.should.have.key("Created")
    revision.should.have.key("Description")
    revision.should.have.key("Revision").equals(1)


@mock_mq
def test_create_configuration_for_rabbitmq():
    client = boto3.client("mq", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        client.create_configuration(
            EngineType="RABBITMQ", EngineVersion="rabbit1", Name="myconfig"
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("BadRequestException")
    err["Message"].should.equal(
        "Broker engine type [RABBITMQ] does not support configuration."
    )


@mock_mq
def test_create_configuration_for_unknown_engine():
    client = boto3.client("mq", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        client.create_configuration(
            EngineType="unknown", EngineVersion="rabbit1", Name="myconfig"
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("BadRequestException")
    err["Message"].should.equal(
        "Broker engine type [unknown] is invalid. Valid values are: [ACTIVEMQ]"
    )


@mock_mq
def test_describe_configuration():
    client = boto3.client("mq", region_name="eu-north-1")
    config_id = client.create_configuration(
        EngineType="ACTIVEMQ", EngineVersion="active2", Name="myconfig"
    )["Id"]

    resp = client.describe_configuration(ConfigurationId=config_id)

    resp.should.have.key("Id").match("^c-")
    resp.should.have.key("Arn").equals(
        f"arn:aws:mq:eu-north-1:{ACCOUNT_ID}:configuration:{resp['Id']}"
    )
    resp.should.have.key("AuthenticationStrategy").equals("simple")
    resp.should.have.key("Created")
    resp.should.have.key("Name").equals("myconfig")
    resp.should.have.key("LatestRevision")

    revision = resp["LatestRevision"]
    revision.should.have.key("Created")
    revision.should.have.key("Description")
    revision.should.have.key("Revision").equals(1)


@mock_mq
def test_describe_configuration_revision():
    client = boto3.client("mq", region_name="eu-north-1")
    config_id = client.create_configuration(
        EngineType="ActiveMQ", EngineVersion="5.16.3", Name="myconfig"
    )["Id"]

    resp = client.describe_configuration_revision(
        ConfigurationId=config_id, ConfigurationRevision="1"
    )

    resp.should.have.key("ConfigurationId").equals(config_id)
    resp.should.have.key("Created")
    resp.should.have.key("Description").equals(
        "Auto-generated default for myconfig on ActiveMQ 5.16.3"
    )

    resp.should.have.key("Data")


@mock_mq
def test_describe_configuration_unknown():
    client = boto3.client("mq", region_name="us-east-2")

    with pytest.raises(ClientError) as exc:
        client.describe_configuration(ConfigurationId="c-unknown")
    err = exc.value.response["Error"]

    err["Code"].should.equal("NotFoundException")
    err["Message"].should.equal(
        "Can't find requested configuration [c-unknown]. Make sure your configuration exists."
    )


@mock_mq
def test_list_configurations_empty():
    client = boto3.client("mq", region_name="us-east-2")

    resp = client.list_configurations()

    resp.should.have.key("Configurations").equals([])


@mock_mq
def test_list_configurations():
    client = boto3.client("mq", region_name="ap-southeast-1")
    config_id = client.create_configuration(
        EngineType="ACTIVEMQ", EngineVersion="active1", Name="myconfig"
    )["Id"]

    resp = client.list_configurations()

    resp.should.have.key("Configurations").length_of(1)

    config = resp["Configurations"][0]
    config.should.have.key("Arn").match("arn:aws")
    config.should.have.key("Created")
    config.should.have.key("Id").equals(config_id)
    config.should.have.key("Name").equals("myconfig")
    config.should.have.key("EngineType").equals("ACTIVEMQ")
    config.should.have.key("EngineVersion").equals("active1")


@mock_mq
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

    resp.should.have.key("Arn").match("arn:aws:mq")
    resp.should.have.key("Created")
    resp.should.have.key("Id")
    resp.should.have.key("Name").equals("myconfig")
    resp.should.have.key("LatestRevision")

    revision = resp["LatestRevision"]
    revision.should.have.key("Created")
    revision.should.have.key("Description").equals("updated config")
    revision.should.have.key("Revision").equals(2)


@mock_mq
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

    resp.should.have.key("AuthenticationStrategy").equals("ldap")
