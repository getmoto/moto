"""Unit tests for timestreaminfluxdb-supported APIs."""

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


"""Unit tests for timestreaminfluxdb-supported APIs."""


@mock_aws
def test_create_db_instance_success():
    client = boto3.client("timestream-influxdb", region_name="us-east-1")

    response = client.create_db_instance(
        name="test-instance",
        password="password123",
        dbInstanceType="db.influx.medium",
        vpcSubnetIds=["subnet-0123456789abcdef0"],
        vpcSecurityGroupIds=["sg-0123456789abcdef0"],
        allocatedStorage=123,
    )

    assert response["allocatedStorage"] == 123
    assert response["dbInstanceType"] == "db.influx.medium"
    assert response["name"] == "test-instance"
    assert response["vpcSecurityGroupIds"] == ["sg-0123456789abcdef0"]
    assert response["vpcSubnetIds"] == ["subnet-0123456789abcdef0"]

    assert "arn" in response
    assert "availabilityZone" in response
    assert "dbStorageType" in response
    assert "deploymentType" in response
    assert "endpoint" in response
    assert "id" in response
    assert "influxAuthParametersSecretArn" in response
    assert "networkType" in response
    assert "port" in response
    assert "publiclyAccessible" in response
    assert "secondaryAvailabilityZone" in response
    assert "status" in response
    assert "logDeliveryConfiguration" in response


@mock_aws
def test_create_db_instance_duplicate_identifier():
    client = boto3.client("timestream-influxdb", region_name="us-east-1")

    client.create_db_instance(
        name="test-instance",
        password="password123",
        dbInstanceType="db.influx.medium",
        vpcSubnetIds=["subnet-0123456789abcdef0"],
        vpcSecurityGroupIds=["sg-0123456789abcdef0"],
        allocatedStorage=123,
    )

    with pytest.raises(ClientError) as exc:
        client.create_db_instance(
            name="test-instance",
            password="password123",
            dbInstanceType="db.influx.medium",
            vpcSubnetIds=["subnet-0123456789abcdef0"],
            vpcSecurityGroupIds=["sg-0123456789abcdef0"],
            allocatedStorage=123,
        )

    assert exc.value.response["Error"]["Code"] == "ConflictException"


@mock_aws
def test_create_db_instance_name_invalid():
    invalid_names = [
        "1muststartwithletter",
        "cantendwithhyphen_",
        "nodoublehyphen--",
        "no",
        "longlonglonglonglonglonglonglonglonglongname",
    ]
    client = boto3.client("timestream-influxdb", region_name="us-east-1")

    for invalid_name in invalid_names:
        with pytest.raises(ClientError) as exc:
            client.create_db_instance(
                name="invalid_name",
                password="password123",
                dbInstanceType="db.influx.medium",
                vpcSubnetIds=["subnet-0123456789abcdef0"],
                vpcSecurityGroupIds=["sg-0123456789abcdef0"],
                allocatedStorage=123,
            )
        assert exc.value.response["Error"]["Code"] == "ValidationException"


@mock_aws
def test_create_db_instance_invalid_storage_type():
    client = boto3.client("timestream-influxdb", region_name="us-east-1")
    with pytest.raises(ClientError) as exc:
        client.create_db_instance(
            name="test-instance",
            password="password123",
            dbInstanceType="db.influx.medium",
            vpcSubnetIds=["subnet-0123456789abcdef0"],
            vpcSecurityGroupIds=["sg-0123456789abcdef0"],
            allocatedStorage=123,
            dbStorageType="invalid",
        )

        assert exc.value.response["Error"]["Code"] == "ValidationException"


@mock_aws
def test_create_db_instance_invalid_instance_type():
    client = boto3.client("timestream-influxdb", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        client.create_db_instance(
            name="test-instance",
            password="password123",
            vpcSubnetIds=["subnet-0123456789abcdef0"],
            vpcSecurityGroupIds=["sg-0123456789abcdef0"],
            allocatedStorage=123,
            dbInstanceType="invalid",
        )

    assert exc.value.response["Error"]["Code"] == "ValidationException"


@mock_aws
def test_delete_db_instance():
    client = boto3.client("timestream-influxdb", region_name="us-east-1")

    response = client.create_db_instance(
        name="test-instance",
        password="password123",
        dbInstanceType="db.influx.medium",
        vpcSubnetIds=["subnet-0123456789abcdef0"],
        vpcSecurityGroupIds=["sg-0123456789abcdef0"],
        allocatedStorage=123,
    )

    id = response["id"]

    response = client.delete_db_instance(identifier=id)
    assert response["allocatedStorage"] == 123
    assert response["dbInstanceType"] == "db.influx.medium"
    assert response["name"] == "test-instance"
    assert response["vpcSecurityGroupIds"] == ["sg-0123456789abcdef0"]
    assert response["vpcSubnetIds"] == ["subnet-0123456789abcdef0"]

    assert "arn" in response
    assert "availabilityZone" in response
    assert "dbStorageType" in response
    assert "deploymentType" in response
    assert "endpoint" in response
    assert "id" in response
    assert "influxAuthParametersSecretArn" in response
    assert "networkType" in response
    assert "port" in response
    assert "publiclyAccessible" in response
    assert "secondaryAvailabilityZone" in response
    assert "logDeliveryConfiguration" in response

    assert response["status"] == "DELETING"


@mock_aws
def test_delete_db_instance_invalid_name():
    client = boto3.client("timestream-influxdb", region_name="us-east-1")

    id = "-100000"
    with pytest.raises(ClientError) as exc:
        client.delete_db_instance(identifier=id)

    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_get_db_instance():
    client = boto3.client("timestream-influxdb", region_name="us-east-1")

    created_instance = client.create_db_instance(
        name="test-instance",
        password="password123",
        dbInstanceType="db.influx.medium",
        vpcSubnetIds=["subnet-0123456789abcdef0"],
        vpcSecurityGroupIds=["sg-0123456789abcdef0"],
        allocatedStorage=123,
    )

    id = created_instance["id"]
    response = client.get_db_instance(identifier=id)
    assert response["allocatedStorage"] == 123
    assert response["dbInstanceType"] == "db.influx.medium"
    assert response["name"] == "test-instance"
    assert response["vpcSecurityGroupIds"] == ["sg-0123456789abcdef0"]
    assert response["vpcSubnetIds"] == ["subnet-0123456789abcdef0"]

    assert "arn" in response
    assert "availabilityZone" in response
    assert "dbStorageType" in response
    assert "deploymentType" in response
    assert "endpoint" in response
    assert "id" in response
    assert "influxAuthParametersSecretArn" in response
    assert "networkType" in response
    assert "port" in response
    assert "publiclyAccessible" in response
    assert "secondaryAvailabilityZone" in response
    assert "logDeliveryConfiguration" in response
    assert "status" in response


@mock_aws
def test_get_db_instance_invalid():
    client = boto3.client("timestream-influxdb", region_name="us-east-1")

    id = "-100000"
    with pytest.raises(ClientError) as exc:
        client.get_db_instance(identifier=id)

    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_list_db_instances_empty():
    client = boto3.client("timestream-influxdb", region_name="us-east-1")
    response = client.list_db_instances()
    assert len(response["items"]) == 0


@mock_aws
def test_list_db_instances():
    client = boto3.client("timestream-influxdb", region_name="us-east-1")
    client.create_db_instance(
        name="test-instance1",
        password="password123",
        dbInstanceType="db.influx.medium",
        vpcSubnetIds=["subnet-0123456789abcdef0"],
        vpcSecurityGroupIds=["sg-0123456789abcdef0"],
        allocatedStorage=123,
    )

    client.create_db_instance(
        name="test-instance2",
        password="password123",
        dbInstanceType="db.influx.medium",
        vpcSubnetIds=["subnet-0123456789abcdef0"],
        vpcSecurityGroupIds=["sg-0123456789abcdef0"],
        allocatedStorage=123,
    )

    response = client.list_db_instances()
    resources = response["items"]
    assert len(resources) == 2

    for resource in resources:
        assert "allocatedStorage" in resource
        assert "arn" in resource
        assert "dbInstanceType" in resource
        assert "dbStorageType" in resource
        assert "deploymentType" in resource
        assert "endpoint" in resource
        assert "id" in resource
        assert "name" in resource
        assert "networkType" in resource
        assert "port" in resource
        assert "status" in resource

    # delete one and confirm only one left
    client.delete_db_instance(identifier=resources[0]["id"])

    response = client.list_db_instances()
    resources = response["items"]
    assert len(resources) == 1
