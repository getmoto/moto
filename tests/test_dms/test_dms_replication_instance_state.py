from unittest import SkipTest

import boto3
import pytest

from moto import mock_aws, settings
from moto.moto_api import state_manager


@pytest.fixture(scope="function")
def execution_state_transition():
    state_manager.set_transition(
        model_name="dms::replicationinstance",
        transition={"progression": "manual", "times": 2},
    )
    yield
    # Reset to default - we don't want to affect other tests
    state_manager.set_transition(
        model_name="dms::replicationinstance",
        transition={"progression": "manual", "times": 1},
    )


@mock_aws
def test_describe_replication_instance_manual_transition(execution_state_transition):
    if not settings.TEST_DECORATOR_MODE:
        # We already test the state transitions in ServerMode in other tests
        raise SkipTest(
            "NO point in verifying state transitions when not using the decorator"
        )

    client = boto3.client("dms", region_name="eu-west-1")
    response = client.create_replication_instance(
        ReplicationInstanceIdentifier="test-instance",
        ReplicationInstanceClass="dms.t2.micro",
        AllocatedStorage=50,
        VpcSecurityGroupIds=["sg-12345"],
        AvailabilityZone="us-east-1a",
        ReplicationSubnetGroupIdentifier="default-subnet-group",
        PreferredMaintenanceWindow="sun:06:00-sun:14:00",
        MultiAZ=False,
        EngineVersion="3.4.6",
        AutoMinorVersionUpgrade=True,
        Tags=[{"Key": "Name", "Value": "Test Instance"}],
        PubliclyAccessible=True,
        NetworkType="IPV4",
    )

    instance = response["ReplicationInstance"]
    assert instance["ReplicationInstanceIdentifier"] == "test-instance"
    assert instance["ReplicationInstanceClass"] == "dms.t2.micro"
    assert instance["AllocatedStorage"] == 50
    assert instance["AvailabilityZone"] == "us-east-1a"
    assert instance["ReplicationInstanceStatus"] == "creating"
    assert instance["MultiAZ"] is False
    assert instance["EngineVersion"] == "3.4.6"
    assert instance["AutoMinorVersionUpgrade"] is True
    assert instance["PubliclyAccessible"] is True
    assert instance["NetworkType"] == "IPV4"
    assert instance["VpcSecurityGroups"] == [
        {"Status": "active", "VpcSecurityGroupId": "sg-12345"}
    ]

    # first call status should stay creating
    response = client.describe_replication_instances(
        Filters=[{"Name": "replication-instance-id", "Values": ["test-instance"]}]
    )
    assert len(response["ReplicationInstances"]) == 1
    instance = response["ReplicationInstances"][0]
    assert instance["ReplicationInstanceIdentifier"] == "test-instance"
    assert instance["ReplicationInstanceClass"] == "dms.t2.micro"
    assert instance["AllocatedStorage"] == 50
    assert instance["AvailabilityZone"] == "us-east-1a"
    assert instance["ReplicationInstanceStatus"] == "creating"
    assert instance["MultiAZ"] is False
    assert instance["EngineVersion"] == "3.4.6"
    assert instance["AutoMinorVersionUpgrade"] is True
    assert instance["PubliclyAccessible"] is True
    assert instance["NetworkType"] == "IPV4"
    assert instance["VpcSecurityGroups"] == [
        {"Status": "active", "VpcSecurityGroupId": "sg-12345"}
    ]

    # Second call should update the status to available
    response = client.describe_replication_instances(
        Filters=[{"Name": "replication-instance-id", "Values": ["test-instance"]}]
    )
    assert len(response["ReplicationInstances"]) == 1
    instance = response["ReplicationInstances"][0]
    assert instance["ReplicationInstanceIdentifier"] == "test-instance"
    assert instance["ReplicationInstanceClass"] == "dms.t2.micro"
    assert instance["AllocatedStorage"] == 50
    assert instance["AvailabilityZone"] == "us-east-1a"
    assert instance["ReplicationInstanceStatus"] == "available"
    assert instance["MultiAZ"] is False
    assert instance["EngineVersion"] == "3.4.6"
    assert instance["AutoMinorVersionUpgrade"] is True
    assert instance["PubliclyAccessible"] is True
    assert instance["NetworkType"] == "IPV4"
    assert instance["VpcSecurityGroups"] == [
        {"Status": "active", "VpcSecurityGroupId": "sg-12345"}
    ]


@mock_aws
def test_replication_instance_without_transition():
    """
    Default state transition is 'manual', with 1 times  meaning that the first time we call describe_replication_instance the status advances
    """

    client = boto3.client("dms", region_name="eu-west-1")
    response = client.create_replication_instance(
        ReplicationInstanceIdentifier="test-instance",
        ReplicationInstanceClass="dms.t2.micro",
        AllocatedStorage=50,
        VpcSecurityGroupIds=["sg-12345"],
        AvailabilityZone="us-east-1a",
        ReplicationSubnetGroupIdentifier="default-subnet-group",
        PreferredMaintenanceWindow="sun:06:00-sun:14:00",
        MultiAZ=False,
        EngineVersion="3.4.6",
        AutoMinorVersionUpgrade=True,
        Tags=[{"Key": "Name", "Value": "Test Instance"}],
        PubliclyAccessible=True,
        NetworkType="IPV4",
    )

    instance = response["ReplicationInstance"]
    assert instance["ReplicationInstanceIdentifier"] == "test-instance"
    assert instance["ReplicationInstanceClass"] == "dms.t2.micro"
    assert instance["AllocatedStorage"] == 50
    assert instance["AvailabilityZone"] == "us-east-1a"
    assert instance["ReplicationInstanceStatus"] == "creating"
    assert instance["MultiAZ"] is False
    assert instance["EngineVersion"] == "3.4.6"
    assert instance["AutoMinorVersionUpgrade"] is True
    assert instance["PubliclyAccessible"] is True
    assert instance["NetworkType"] == "IPV4"
    assert instance["VpcSecurityGroups"] == [
        {"Status": "active", "VpcSecurityGroupId": "sg-12345"}
    ]

    # first call status should advance the state
    response = client.describe_replication_instances(
        Filters=[{"Name": "replication-instance-id", "Values": ["test-instance"]}]
    )
    assert len(response["ReplicationInstances"]) == 1
    instance = response["ReplicationInstances"][0]
    assert instance["ReplicationInstanceIdentifier"] == "test-instance"
    assert instance["ReplicationInstanceClass"] == "dms.t2.micro"
    assert instance["AllocatedStorage"] == 50
    assert instance["AvailabilityZone"] == "us-east-1a"
    assert instance["ReplicationInstanceStatus"] == "available"
    assert instance["MultiAZ"] is False
    assert instance["EngineVersion"] == "3.4.6"
    assert instance["AutoMinorVersionUpgrade"] is True
    assert instance["PubliclyAccessible"] is True
    assert instance["NetworkType"] == "IPV4"
    assert instance["VpcSecurityGroups"] == [
        {"Status": "active", "VpcSecurityGroupId": "sg-12345"}
    ]
