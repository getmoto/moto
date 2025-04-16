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


@mock_aws
def test_create_db_parameter_group():
    client = boto3.client("timestream-influxdb", region_name="us-east-1")

    response = client.create_db_parameter_group(
        name="test-parameter-group",
        description="Test parameter group for unit tests",
        parameters={
            "InfluxDBv2": {
                "fluxLogEnabled": True,
                "logLevel": "debug",
                "queryQueueSize": 100,
            }
        },
        tags={"Environment": "Test", "Project": "Moto"},
    )

    assert response["name"] == "test-parameter-group"
    assert response["description"] == "Test parameter group for unit tests"
    assert response["parameters"]["InfluxDBv2"]["fluxLogEnabled"] is True
    assert response["parameters"]["InfluxDBv2"]["logLevel"] == "debug"
    assert response["parameters"]["InfluxDBv2"]["queryQueueSize"] == 100
    assert "id" in response
    assert "arn" in response


@mock_aws
def test_get_db_parameter_group():
    client = boto3.client("timestream-influxdb", region_name="us-east-1")

    create_response = client.create_db_parameter_group(
        name="test-parameter-group",
        description="Test parameter group for unit tests",
        parameters={"InfluxDBv2": {"fluxLogEnabled": True, "logLevel": "debug"}},
    )

    param_group_id = create_response["id"]

    get_response = client.get_db_parameter_group(identifier=param_group_id)

    assert get_response["id"] == param_group_id
    assert get_response["name"] == "test-parameter-group"
    assert get_response["description"] == "Test parameter group for unit tests"
    assert get_response["parameters"]["InfluxDBv2"]["fluxLogEnabled"] is True
    assert get_response["parameters"]["InfluxDBv2"]["logLevel"] == "debug"
    assert "arn" in get_response

    with pytest.raises(ClientError) as exc:
        client.get_db_parameter_group(identifier="non-existent-id")

    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_list_db_parameter_groups():
    client = boto3.client("timestream-influxdb", region_name="us-east-1")

    list_response = client.list_db_parameter_groups()
    assert len(list_response["items"]) == 0
    assert "nextToken" not in list_response

    param_groups = []
    for i in range(5):
        response = client.create_db_parameter_group(
            name=f"test-parameter-group-{i}",
            description=f"Test parameter group {i}",
            parameters={
                "InfluxDBv2": {
                    "fluxLogEnabled": i % 2 == 0,
                    "logLevel": "debug" if i % 2 == 0 else "info",
                }
            },
        )
        param_groups.append(response)

    list_response = client.list_db_parameter_groups()
    assert len(list_response["items"]) == 5

    list_response = client.list_db_parameter_groups(maxResults=2)
    assert len(list_response["items"]) == 2
    assert "nextToken" in list_response

    next_token = list_response["nextToken"]
    list_response = client.list_db_parameter_groups(nextToken=next_token, maxResults=2)
    assert len(list_response["items"]) == 2
    assert "nextToken" in list_response

    next_token = list_response["nextToken"]
    list_response = client.list_db_parameter_groups(nextToken=next_token, maxResults=2)
    assert len(list_response["items"]) == 1
    assert "nextToken" not in list_response


@mock_aws
def test_list_db_clusters():
    client = boto3.client("timestream-influxdb", region_name="us-east-1")

    list_response = client.list_db_clusters()
    assert len(list_response["items"]) == 0
    assert "nextToken" not in list_response

    cluster_ids = []
    for i in range(5):
        response = client.create_db_cluster(
            name=f"test-cluster-{i}",
            password="password123",
            dbInstanceType="db.influx.medium",
            allocatedStorage=100,
            vpcSubnetIds=["subnet-0123456789abcdef0", "subnet-0123456789abcdef1"],
            vpcSecurityGroupIds=["sg-0123456789abcdef0"],
            deploymentType="MULTI_NODE_READ_REPLICAS",
        )
        cluster_ids.append(response["dbClusterId"])

    list_response = client.list_db_clusters()
    assert len(list_response["items"]) == 5

    for item in list_response["items"]:
        assert "id" in item
        assert "name" in item
        assert "arn" in item
        assert "status" in item
        assert "endpoint" in item
        assert "readerEndpoint" in item
        assert "port" in item
        assert "deploymentType" in item
        assert "dbInstanceType" in item
        assert "networkType" in item
        assert "dbStorageType" in item
        assert "allocatedStorage" in item

    list_response = client.list_db_clusters(maxResults=2)
    assert len(list_response["items"]) == 2
    assert "nextToken" in list_response

    next_token = list_response["nextToken"]
    list_response = client.list_db_clusters(nextToken=next_token, maxResults=2)
    assert len(list_response["items"]) == 2
    assert "nextToken" in list_response

    next_token = list_response["nextToken"]
    list_response = client.list_db_clusters(nextToken=next_token, maxResults=2)
    assert len(list_response["items"]) == 1
    assert "nextToken" not in list_response


@mock_aws
def test_get_db_cluster():
    client = boto3.client("timestream-influxdb", region_name="us-east-1")

    create_response = client.create_db_cluster(
        name="test-cluster",
        password="password123",
        dbInstanceType="db.influx.medium",
        allocatedStorage=100,
        vpcSubnetIds=["subnet-0123456789abcdef0", "subnet-0123456789abcdef1"],
        vpcSecurityGroupIds=["sg-0123456789abcdef0"],
        deploymentType="MULTI_NODE_READ_REPLICAS",
    )

    cluster_id = create_response["dbClusterId"]

    get_response = client.get_db_cluster(dbClusterId=cluster_id)

    assert get_response["id"] == cluster_id
    assert get_response["name"] == "test-cluster"
    assert get_response["status"] == "AVAILABLE"
    assert get_response["deploymentType"] == "MULTI_NODE_READ_REPLICAS"
    assert get_response["dbInstanceType"] == "db.influx.medium"
    assert get_response["allocatedStorage"] == 100
    assert isinstance(get_response["arn"], str)
    assert isinstance(get_response["endpoint"], str)
    assert isinstance(get_response["readerEndpoint"], str)
    assert isinstance(get_response["port"], int)
    assert isinstance(get_response["vpcSubnetIds"], list)
    assert isinstance(get_response["vpcSecurityGroupIds"], list)
    assert len(get_response["vpcSubnetIds"]) == 2
    assert len(get_response["vpcSecurityGroupIds"]) == 1

    with pytest.raises(ClientError) as exc:
        client.get_db_cluster(dbClusterId="non-existent-id")

    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_create_db_cluster():
    client = boto3.client("timestream-influxdb", region_name="us-east-1")

    response = client.create_db_cluster(
        name="test-cluster",
        password="password123",
        dbInstanceType="db.influx.medium",
        allocatedStorage=100,
        vpcSubnetIds=["subnet-0123456789abcdef0", "subnet-0123456789abcdef1"],
        vpcSecurityGroupIds=["sg-0123456789abcdef0"],
        deploymentType="MULTI_NODE_READ_REPLICAS",
    )

    assert "dbClusterId" in response
    assert response["dbClusterStatus"] == "AVAILABLE"

    with pytest.raises(ClientError) as exc:
        client.create_db_cluster(
            name="test-cluster",
            password="password123",
            dbInstanceType="db.influx.medium",
            allocatedStorage=100,
            vpcSubnetIds=["subnet-0123456789abcdef0", "subnet-0123456789abcdef1"],
            vpcSecurityGroupIds=["sg-0123456789abcdef0"],
            deploymentType="MULTI_NODE_READ_REPLICAS",
        )

    assert exc.value.response["Error"]["Code"] == "ConflictException"

    response = client.create_db_cluster(
        name="test-cluster-full",
        username="admin",
        password="password123",
        organization="test-org",
        bucket="test-bucket",
        port=8088,
        dbParameterGroupIdentifier="test-param-group",
        dbInstanceType="db.influx.medium",
        dbStorageType="InfluxIOIncludedT1",
        allocatedStorage=100,
        networkType="IPV4",
        publiclyAccessible=True,
        vpcSubnetIds=["subnet-0123456789abcdef0", "subnet-0123456789abcdef1"],
        vpcSecurityGroupIds=["sg-0123456789abcdef0"],
        deploymentType="MULTI_NODE_READ_REPLICAS",
        failoverMode="AUTOMATIC",
        logDeliveryConfiguration={
            "s3Configuration": {"bucketName": "test-bucket", "enabled": True}
        },
        tags={"Environment": "Test", "Project": "Moto"},
    )

    assert "dbClusterId" in response
    assert response["dbClusterStatus"] == "AVAILABLE"
