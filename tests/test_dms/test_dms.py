import json

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws


@mock_aws
def test_create_and_get_replication_task():
    client = boto3.client("dms", region_name="us-east-1")

    client.create_replication_task(
        ReplicationTaskIdentifier="test",
        SourceEndpointArn="source-endpoint-arn",
        TargetEndpointArn="target-endpoint-arn",
        ReplicationInstanceArn="replication-instance-arn",
        MigrationType="full-load",
        TableMappings='{"rules":[]}',
        ReplicationTaskSettings='{"Logging":{} }',
    )

    tasks = client.describe_replication_tasks(
        Filters=[
            {"Name": "replication-task-id", "Values": ["test"]},
            {"Name": "migration-type", "Values": ["full-load"]},
            {
                "Name": "endpoint-arn",
                "Values": ["source-endpoint-arn", "target-endpoint-arn"],
            },
            {
                "Name": "replication-instance-arn",
                "Values": ["replication-instance-arn"],
            },
        ]
    )

    assert len(tasks["ReplicationTasks"]) == 1
    task = tasks["ReplicationTasks"][0]
    assert task["ReplicationTaskIdentifier"] == "test"
    assert task["SourceEndpointArn"] == "source-endpoint-arn"
    assert task["TargetEndpointArn"] == "target-endpoint-arn"
    assert task["ReplicationInstanceArn"] == "replication-instance-arn"
    assert task["MigrationType"] == "full-load"
    assert task["Status"] == "creating"
    assert task["TableMappings"] == '{"rules":[]}'
    assert isinstance(json.loads(task["TableMappings"]), dict)

    assert task["ReplicationTaskSettings"] == '{"Logging":{} }'
    assert isinstance(json.loads(task["ReplicationTaskSettings"]), dict)


@mock_aws
def test_create_existing_replication_task_throws_error():
    client = boto3.client("dms", region_name="us-east-1")

    client.create_replication_task(
        ReplicationTaskIdentifier="test",
        SourceEndpointArn="source-endpoint-arn",
        TargetEndpointArn="target-endpoint-arn",
        ReplicationInstanceArn="replication-instance-arn",
        MigrationType="full-load",
        TableMappings='{"rules":[]}',
    )

    with pytest.raises(ClientError) as ex:
        client.create_replication_task(
            ReplicationTaskIdentifier="test",
            SourceEndpointArn="source-endpoint-arn",
            TargetEndpointArn="target-endpoint-arn",
            ReplicationInstanceArn="replication-instance-arn",
            MigrationType="full-load",
            TableMappings='{"rules":[]}',
        )

    assert ex.value.operation_name == "CreateReplicationTask"
    assert ex.value.response["Error"]["Code"] == "ResourceAlreadyExistsFault"
    assert (
        ex.value.response["Error"]["Message"]
        == "The resource you are attempting to create already exists."
    )


@mock_aws
def test_start_replication_task():
    client = boto3.client("dms", region_name="us-east-1")

    response = client.create_replication_task(
        ReplicationTaskIdentifier="test",
        SourceEndpointArn="source-endpoint-arn",
        TargetEndpointArn="target-endpoint-arn",
        ReplicationInstanceArn="replication-instance-arn",
        MigrationType="full-load",
        TableMappings='{"rules":[]}',
    )
    task_arn = response["ReplicationTask"]["ReplicationTaskArn"]
    client.start_replication_task(
        ReplicationTaskArn=task_arn, StartReplicationTaskType="start-replication"
    )
    tasks = client.describe_replication_tasks(
        Filters=[{"Name": "replication-task-arn", "Values": [task_arn]}]
    )

    assert tasks["ReplicationTasks"][0]["Status"] == "running"


@mock_aws
def test_start_replication_task_throws_resource_not_found_error():
    client = boto3.client("dms", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.start_replication_task(
            ReplicationTaskArn="does-not-exist",
            StartReplicationTaskType="start-replication",
        )

    assert ex.value.operation_name == "StartReplicationTask"
    assert ex.value.response["Error"]["Code"] == "ResourceNotFoundFault"
    assert (
        ex.value.response["Error"]["Message"] == "Replication task could not be found."
    )


@mock_aws
def test_stop_replication_task_throws_invalid_state_error():
    client = boto3.client("dms", region_name="us-east-1")

    response = client.create_replication_task(
        ReplicationTaskIdentifier="test",
        SourceEndpointArn="source-endpoint-arn",
        TargetEndpointArn="target-endpoint-arn",
        ReplicationInstanceArn="replication-instance-arn",
        MigrationType="full-load",
        TableMappings='{"rules":[]}',
    )
    task_arn = response["ReplicationTask"]["ReplicationTaskArn"]

    with pytest.raises(ClientError) as ex:
        client.stop_replication_task(ReplicationTaskArn=task_arn)

    assert ex.value.operation_name == "StopReplicationTask"
    assert ex.value.response["Error"]["Code"] == "InvalidResourceStateFault"
    assert ex.value.response["Error"]["Message"] == "Replication task is not running"


@mock_aws
def test_stop_replication_task_throws_resource_not_found_error():
    client = boto3.client("dms", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.stop_replication_task(ReplicationTaskArn="does-not-exist")

    assert ex.value.operation_name == "StopReplicationTask"
    assert ex.value.response["Error"]["Code"] == "ResourceNotFoundFault"
    assert (
        ex.value.response["Error"]["Message"] == "Replication task could not be found."
    )


@mock_aws
def test_stop_replication_task():
    client = boto3.client("dms", region_name="us-east-1")

    response = client.create_replication_task(
        ReplicationTaskIdentifier="test",
        SourceEndpointArn="source-endpoint-arn",
        TargetEndpointArn="target-endpoint-arn",
        ReplicationInstanceArn="replication-instance-arn",
        MigrationType="full-load",
        TableMappings='{"rules":[]}',
    )
    task_arn = response["ReplicationTask"]["ReplicationTaskArn"]
    client.start_replication_task(
        ReplicationTaskArn=task_arn, StartReplicationTaskType="start-replication"
    )
    client.stop_replication_task(ReplicationTaskArn=task_arn)
    tasks = client.describe_replication_tasks(
        Filters=[{"Name": "replication-task-arn", "Values": [task_arn]}]
    )

    assert tasks["ReplicationTasks"][0]["Status"] == "stopped"


@mock_aws
def test_delete_replication_task():
    client = boto3.client("dms", region_name="us-east-1")

    response = client.create_replication_task(
        ReplicationTaskIdentifier="test",
        SourceEndpointArn="source-endpoint-arn",
        TargetEndpointArn="target-endpoint-arn",
        ReplicationInstanceArn="replication-instance-arn",
        MigrationType="full-load",
        TableMappings='{"rules":[]}',
    )
    task_arn = response["ReplicationTask"]["ReplicationTaskArn"]
    client.delete_replication_task(ReplicationTaskArn=task_arn)
    tasks = client.describe_replication_tasks(
        Filters=[{"Name": "replication-task-arn", "Values": [task_arn]}]
    )

    assert len(tasks["ReplicationTasks"]) == 0


@mock_aws
def test_delete_replication_task_throws_resource_not_found_error():
    client = boto3.client("dms", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.delete_replication_task(ReplicationTaskArn="does-not-exist")

    assert ex.value.operation_name == "DeleteReplicationTask"
    assert ex.value.response["Error"]["Code"] == "ResourceNotFoundFault"
    assert (
        ex.value.response["Error"]["Message"] == "Replication task could not be found."
    )


@mock_aws
def test_create_replication_instance():
    client = boto3.client("dms", region_name="us-east-1")

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

    arn = instance["ReplicationInstanceArn"]
    assert arn.startswith("arn:aws:dms:us-east-1:")
    assert ":rep:test-instance" in arn

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
def test_describe_replication_instances():
    client = boto3.client("dms", region_name="us-east-1")

    client.create_replication_instance(
        ReplicationInstanceIdentifier="test-instance-1",
        ReplicationInstanceClass="dms.t2.micro",
        EngineVersion="3.4.5",
    )

    client.create_replication_instance(
        ReplicationInstanceIdentifier="test-instance-2",
        ReplicationInstanceClass="dms.t2.small",
        EngineVersion="3.4.6",
    )

    response = client.describe_replication_instances()
    instances = response["ReplicationInstances"]
    assert len(instances) == 2

    response = client.describe_replication_instances(
        Filters=[{"Name": "replication-instance-class", "Values": ["dms.t2.micro"]}]
    )
    instances = response["ReplicationInstances"]
    assert len(instances) == 1
    assert instances[0]["ReplicationInstanceIdentifier"] == "test-instance-1"

    response = client.describe_replication_instances(
        Filters=[{"Name": "engine-version", "Values": ["3.4.6"]}]
    )
    instances = response["ReplicationInstances"]
    assert len(instances) == 1
    assert instances[0]["ReplicationInstanceIdentifier"] == "test-instance-2"


@mock_aws
def test_delete_replication_instance():
    client = boto3.client("dms", region_name="us-east-2")

    response = client.create_replication_instance(
        ReplicationInstanceIdentifier="test-instance-1",
        ReplicationInstanceClass="dms.t2.micro",
        EngineVersion="3.4.5",
    )
    replication_instance_arn = response["ReplicationInstance"]["ReplicationInstanceArn"]
    client.delete_replication_instance(ReplicationInstanceArn=replication_instance_arn)
    replication_instances = client.describe_replication_instances(
        Filters=[
            {"Name": "replication-instance-arn", "Values": [replication_instance_arn]}
        ]
    )

    assert len(replication_instances["ReplicationInstances"]) == 0


@mock_aws
def test_delete_replication_instance_throws_resource_not_found_error():
    client = boto3.client("dms", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.delete_replication_instance(ReplicationInstanceArn="does-not-exist")

    assert ex.value.operation_name == "DeleteReplicationInstance"
    assert ex.value.response["Error"]["Code"] == "ResourceNotFoundFault"
    assert (
        ex.value.response["Error"]["Message"]
        == "Replication instance could not be found."
    )


@mock_aws
def test_create_endpoint():
    region_name = "ap-southeast-1"
    client = boto3.client("dms", region_name=region_name)

    response = client.create_endpoint(
        EndpointIdentifier="test-endpoint",
        EndpointType="source",
        EngineName="mysql",
        Username="admin",
        ServerName="test-server",
        Port=3306,
        DatabaseName="test-db",
        ExtraConnectionAttributes="",
        KmsKeyId="test-kms-key-id",
        CertificateArn="test-certificate-arn",
        SslMode="require",
        ServiceAccessRoleArn="test-service-role-arn",
        ExternalTableDefinition="",
    )

    endpoint = response["Endpoint"]

    # Assertions for the required fields
    assert endpoint["EndpointIdentifier"] == "test-endpoint"
    assert endpoint["EndpointType"] == "source"
    assert endpoint["EngineName"] == "mysql"
    assert endpoint["Username"] == "admin"
    assert endpoint["ServerName"] == "test-server"
    assert endpoint["Port"] == 3306
    assert endpoint["DatabaseName"] == "test-db"
    assert endpoint["Status"] == "creating"
    assert endpoint["KmsKeyId"] == "test-kms-key-id"
    assert (
        f"arn:aws:dms:{region_name}:123456789012:endpoint:" in endpoint["EndpointArn"]
    )
    assert endpoint["SslMode"] == "require"


@mock_aws
def test_create_endpoint_resource_identifier():
    client = boto3.client("dms", region_name="ap-southeast-1")

    resource_identifier = "test-resource-identifier"
    response = client.create_endpoint(
        EndpointIdentifier="test-endpoint",
        EndpointType="source",
        EngineName="mysql",
        ResourceIdentifier=resource_identifier,
    )

    endpoint = response["Endpoint"]

    # Assertions for the required fields
    assert endpoint["EndpointIdentifier"] == "test-endpoint"
    assert endpoint["EndpointType"] == "source"
    assert endpoint["EngineName"] == "mysql"
    assert resource_identifier == endpoint["EndpointArn"].split(":")[-1]


@mock_aws
def test_describe_endpoints():
    client = boto3.client("dms", region_name="ap-southeast-1")
    num_endpoints = 3
    for i in range(num_endpoints):
        client.create_endpoint(
            EndpointIdentifier=f"test-endpoint-{i}",
            EndpointType="source",
            EngineName="mysql",
        )

    resp = client.describe_endpoints()
    assert len(resp["Endpoints"]) == num_endpoints


@mock_aws
def test_describe_endpoints_filter():
    client = boto3.client("dms", region_name="ap-southeast-1")

    for i in range(3):
        client.create_endpoint(
            EndpointIdentifier=f"test-endpoint-{i}",
            EndpointType="source",
            EngineName="mysql",
        )

    endpoint_filter = {"Name": "endpoint-id", "Values": ["test-endpoint-1"]}
    resp = client.describe_endpoints(Filters=[endpoint_filter])
    assert len(resp["Endpoints"]) == 1

    engine_filter = {"Name": "engine-name", "Values": ["mysql"]}
    resp = client.describe_endpoints(Filters=[engine_filter])
    assert len(resp["Endpoints"]) == 3


@mock_aws
def test_delete_endpoint():
    client = boto3.client("dms", region_name="ap-southeast-1")

    response = client.create_endpoint(
        EndpointIdentifier="test-endpoint",
        EndpointType="source",
        EngineName="mysql",
    )
    endpoint_arn = response["Endpoint"]["EndpointArn"]
    client.delete_endpoint(EndpointArn=endpoint_arn)

    endpoints = client.describe_endpoints(
        Filters=[{"Name": "endpoint-id", "Values": ["test-endpoint"]}]
    )
    assert len(endpoints["Endpoints"]) == 0


@mock_aws
def test_delete_endpoint_throws_resource_not_found_error():
    client = boto3.client("dms", region_name="ap-southeast-1")

    with pytest.raises(ClientError) as ex:
        client.delete_endpoint(EndpointArn="does-not-exist")

    assert ex.value.operation_name == "DeleteEndpoint"
    assert ex.value.response["Error"]["Code"] == "ResourceNotFoundFault"
    assert ex.value.response["Error"]["Message"] == "Endpoint could not be found."


@mock_aws
def test_list_tags_for_resource_replication_instance():
    client = boto3.client("dms", region_name="eu-west-1")

    response = client.create_replication_instance(
        ReplicationInstanceIdentifier="test",
        ReplicationInstanceClass="dms.c4.large",
        Tags=[{"Key": "Environment", "Value": "Production"}],
    )

    arn = response["ReplicationInstance"]["ReplicationInstanceArn"]

    resp = client.list_tags_for_resource(ResourceArn=arn)
    assert resp["TagList"] == [
        {"Key": "Environment", "Value": "Production", "ResourceArn": arn}
    ]


@mock_aws
def test_list_tags_for_resource_endpoint():
    client = boto3.client("dms", region_name="eu-west-1")

    response = client.create_endpoint(
        EndpointIdentifier="test-endpoint",
        EndpointType="source",
        EngineName="mysql",
        Tags=[{"Key": "Name", "Value": "Test Endpoint"}],
    )
    arn = response["Endpoint"]["EndpointArn"]

    resp = client.list_tags_for_resource(ResourceArn=arn)
    assert resp["TagList"] == [
        {"Key": "Name", "Value": "Test Endpoint", "ResourceArn": arn}
    ]


@mock_aws
def test_list_tags_for_resource_endpoints():
    client = boto3.client("dms", region_name="eu-west-1")

    response = client.create_endpoint(
        EndpointIdentifier="test-endpoint",
        EndpointType="source",
        EngineName="mysql",
        Tags=[{"Key": "Name", "Value": "Test Endpoint"}],
    )
    endpoint_arn1 = response["Endpoint"]["EndpointArn"]

    response = client.create_endpoint(
        EndpointIdentifier="test-endpoint",
        EndpointType="source",
        EngineName="mysql",
        Tags=[{"Key": "Name", "Value": "Test Endpoint"}],
    )
    endpoint_arn2 = response["Endpoint"]["EndpointArn"]

    resp = client.list_tags_for_resource(ResourceArnList=[endpoint_arn1, endpoint_arn2])
    assert len(resp["TagList"]) == 2


@mock_aws
def test_create_replication_subnet_group():
    client = boto3.client("dms", region_name="ap-southeast-1")
    response = client.create_replication_subnet_group(
        ReplicationSubnetGroupIdentifier="test-group",
        ReplicationSubnetGroupDescription="description for test-group",
        SubnetIds=["subnet-12345"],
    )

    replication_subnet_group = response["ReplicationSubnetGroup"]

    assert replication_subnet_group["ReplicationSubnetGroupIdentifier"] == "test-group"
    assert (
        replication_subnet_group["ReplicationSubnetGroupDescription"]
        == "description for test-group"
    )
    assert replication_subnet_group["VpcId"] == "vpc-12345"
    assert replication_subnet_group["SubnetGroupStatus"] == "Complete"


@mock_aws
def test_create_replication_subnet_group_throws_resource_already_exists():
    client = boto3.client("dms", region_name="ap-southeast-1")
    client.create_replication_subnet_group(
        ReplicationSubnetGroupIdentifier="test-group",
        ReplicationSubnetGroupDescription="description for test-group",
        SubnetIds=["subnet-OD12345"],
    )

    with pytest.raises(ClientError) as ex:
        client.create_replication_subnet_group(
            ReplicationSubnetGroupIdentifier="test-group",
            ReplicationSubnetGroupDescription="description for test-group",
            SubnetIds=["subnet-OD12345"],
        )

    assert ex.value.operation_name == "CreateReplicationSubnetGroup"
    assert ex.value.response["Error"]["Code"] == "ResourceAlreadyExistsFault"
    assert (
        ex.value.response["Error"]["Message"]
        == "The resource you are attempting to create already exists."
    )


@mock_aws
def test_describe_replication_subnet_groups():
    client = boto3.client("dms", region_name="ap-southeast-1")
    for i in range(3):
        client.create_replication_subnet_group(
            ReplicationSubnetGroupIdentifier=f"test-group-{i}",
            ReplicationSubnetGroupDescription=f"description for test-group-{i}",
            SubnetIds=["subnet-12345"],
        )

    response = client.describe_replication_subnet_groups()
    assert len(response["ReplicationSubnetGroups"]) == 3

    group_filter = {"Name": "replication-subnet-group-id", "Values": ["test-group-1"]}
    response = client.describe_replication_subnet_groups(Filters=[group_filter])
    assert len(response["ReplicationSubnetGroups"]) == 1

    group_filter = {"Name": "replication-subnet-group-id", "Values": ["no-grou["]}
    response = client.describe_replication_subnet_groups(Filters=[group_filter])
    assert len(response["ReplicationSubnetGroups"]) == 0


@mock_aws
def test_delete_replication_subnet_group():
    client = boto3.client("dms", region_name="eu-west-1")

    client.create_replication_subnet_group(
        ReplicationSubnetGroupIdentifier="test-group",
        ReplicationSubnetGroupDescription="description for test-group",
        SubnetIds=["subnet-12345"],
    )

    client.delete_replication_subnet_group(
        ReplicationSubnetGroupIdentifier="test-group"
    )

    response = client.describe_replication_subnet_groups()
    assert len(response["ReplicationSubnetGroups"]) == 0


@mock_aws
def test_delete_replication_subnet_group_throws_resource_not_found_error():
    client = boto3.client("dms", region_name="eu-west-1")

    with pytest.raises(ClientError) as ex:
        client.delete_replication_subnet_group(
            ReplicationSubnetGroupIdentifier="does-not-exist"
        )

    assert ex.value.operation_name == "DeleteReplicationSubnetGroup"
    assert ex.value.response["Error"]["Code"] == "ResourceNotFoundFault"
    assert (
        ex.value.response["Error"]["Message"]
        == "Replication subnet group could not be found."
    )


@mock_aws
def test_test_connection():
    client = boto3.client("dms", region_name="ap-southeast-1")

    response = client.create_replication_instance(
        ReplicationInstanceIdentifier="test-instance",
        ReplicationInstanceClass="dms.t2.micro",
        EngineVersion="3.4.5",
    )
    replication_instance_arn = response["ReplicationInstance"]["ReplicationInstanceArn"]
    response = client.create_endpoint(
        EndpointIdentifier="test-endpoint",
        EndpointType="source",
        EngineName="mysql",
        Tags=[{"Key": "Name", "Value": "Test Endpoint"}],
    )
    endpoint_arn = response["Endpoint"]["EndpointArn"]
    response = client.test_connection(
        ReplicationInstanceArn=replication_instance_arn, EndpointArn=endpoint_arn
    )
    connection = response["Connection"]
    assert connection["ReplicationInstanceArn"] == replication_instance_arn
    assert connection["EndpointArn"] == endpoint_arn
    assert connection["Status"] == "testing"
    assert connection["EndpointIdentifier"] == "test-endpoint"
    assert connection["ReplicationInstanceIdentifier"] == "test-instance"


@mock_aws
def test_test_connection_throws_resource_not_found_error_for_missing_replication_instance():
    client = boto3.client("dms", region_name="ap-southeast-1")

    response = client.create_endpoint(
        EndpointIdentifier="test-endpoint",
        EndpointType="source",
        EngineName="mysql",
        Tags=[{"Key": "Name", "Value": "Testi Endpoint"}],
    )
    endpoint_arn = response["Endpoint"]["EndpointArn"]

    with pytest.raises(ClientError) as ex:
        response = client.test_connection(
            ReplicationInstanceArn="does-not-exist", EndpointArn=endpoint_arn
        )

    assert ex.value.operation_name == "TestConnection"
    assert ex.value.response["Error"]["Code"] == "ResourceNotFoundFault"
    assert (
        ex.value.response["Error"]["Message"]
        == "Replication instance could not be found."
    )


@mock_aws
def test_test_connection_throws_resource_not_found_error_for_missing_endpoint():
    client = boto3.client("dms", region_name="ap-southeast-1")

    response = client.create_replication_instance(
        ReplicationInstanceIdentifier="test-instance",
        ReplicationInstanceClass="dms.t2.micro",
        EngineVersion="3.4.5",
    )
    replication_instance_arn = response["ReplicationInstance"]["ReplicationInstanceArn"]

    with pytest.raises(ClientError) as ex:
        response = client.test_connection(
            ReplicationInstanceArn=replication_instance_arn,
            EndpointArn="not-a-valid-endpoint",
        )

    assert ex.value.operation_name == "TestConnection"
    assert ex.value.response["Error"]["Code"] == "ResourceNotFoundFault"
    assert ex.value.response["Error"]["Message"] == "Endpoint could not be found."


@mock_aws
def test_describe_connections():
    client = boto3.client("dms", region_name="eu-west-1")
    response = client.create_replication_instance(
        ReplicationInstanceIdentifier="test-instance",
        ReplicationInstanceClass="dms.t2.micro",
        EngineVersion="3.4.5",
    )
    replication_instance_arn = response["ReplicationInstance"]["ReplicationInstanceArn"]
    response = client.create_endpoint(
        EndpointIdentifier="test-endpoint",
        EndpointType="source",
        EngineName="mysql",
        Tags=[{"Key": "Name", "Value": "Test Endpoint"}],
    )
    endpoint_arn = response["Endpoint"]["EndpointArn"]
    response = client.test_connection(
        ReplicationInstanceArn=replication_instance_arn, EndpointArn=endpoint_arn
    )
    connection = response["Connection"]
    assert connection["ReplicationInstanceArn"] == replication_instance_arn
    assert connection["EndpointArn"] == endpoint_arn
    assert connection["Status"] == "testing"
    assert connection["EndpointIdentifier"] == "test-endpoint"
    assert connection["ReplicationInstanceIdentifier"] == "test-instance"

    response = client.describe_connections()
    assert len(response["Connections"]) == 1
    connection = response["Connections"][0]
    assert connection["ReplicationInstanceArn"] == replication_instance_arn
    assert connection["EndpointArn"] == endpoint_arn
    assert connection["Status"] == "successful"
    assert connection["EndpointIdentifier"] == "test-endpoint"
    assert connection["ReplicationInstanceIdentifier"] == "test-instance"


@mock_aws
def test_describe_connections_removal_of_replication_instance_removes_connection():
    client = boto3.client("dms", region_name="eu-west-1")
    response = client.create_replication_instance(
        ReplicationInstanceIdentifier="test-instance-1",
        ReplicationInstanceClass="dms.t2.micro",
        EngineVersion="3.4.5",
    )
    replication_instance_1_arn = response["ReplicationInstance"][
        "ReplicationInstanceArn"
    ]
    response = client.create_endpoint(
        EndpointIdentifier="test-endpoint-1",
        EndpointType="source",
        EngineName="mysql",
        Tags=[{"Key": "Name", "Value": "Test Endpoint"}],
    )
    endpoint_1_arn = response["Endpoint"]["EndpointArn"]
    response = client.test_connection(
        ReplicationInstanceArn=replication_instance_1_arn, EndpointArn=endpoint_1_arn
    )

    response = client.create_replication_instance(
        ReplicationInstanceIdentifier="test-instance-2",
        ReplicationInstanceClass="dms.t2.micro",
        EngineVersion="3.4.5",
    )
    replication_instance_2_arn = response["ReplicationInstance"][
        "ReplicationInstanceArn"
    ]
    response = client.create_endpoint(
        EndpointIdentifier="test-endpoint-2",
        EndpointType="source",
        EngineName="mysql",
        Tags=[{"Key": "Name", "Value": "Test Endpoint"}],
    )
    endpoint_2_arn = response["Endpoint"]["EndpointArn"]
    response = client.test_connection(
        ReplicationInstanceArn=replication_instance_2_arn, EndpointArn=endpoint_2_arn
    )
    response = client.describe_connections()
    assert len(response["Connections"]) == 2

    response = client.describe_replication_instances()
    assert len(response["ReplicationInstances"]) == 2
    client.delete_replication_instance(
        ReplicationInstanceArn=replication_instance_1_arn
    )
    response = client.describe_replication_instances()
    assert len(response["ReplicationInstances"]) == 1

    # The connection should have been removed as its no longer valid
    response = client.describe_connections()
    assert len(response["Connections"]) == 1


@mock_aws
def test_describe_connections_removal_of_endpoint_removes_connection():
    client = boto3.client("dms", region_name="eu-west-1")
    response = client.create_replication_instance(
        ReplicationInstanceIdentifier="test-instance-1",
        ReplicationInstanceClass="dms.t2.micro",
        EngineVersion="3.4.5",
    )
    replication_instance_1_arn = response["ReplicationInstance"][
        "ReplicationInstanceArn"
    ]
    response = client.create_endpoint(
        EndpointIdentifier="test-endpoint-1",
        EndpointType="source",
        EngineName="mysql",
        Tags=[{"Key": "Name", "Value": "Test Endpoint"}],
    )
    endpoint_1_arn = response["Endpoint"]["EndpointArn"]
    response = client.test_connection(
        ReplicationInstanceArn=replication_instance_1_arn, EndpointArn=endpoint_1_arn
    )

    response = client.create_replication_instance(
        ReplicationInstanceIdentifier="test-instance-2",
        ReplicationInstanceClass="dms.t2.micro",
        EngineVersion="3.4.5",
    )
    replication_instance_2_arn = response["ReplicationInstance"][
        "ReplicationInstanceArn"
    ]
    response = client.create_endpoint(
        EndpointIdentifier="test-endpoint-2",
        EndpointType="source",
        EngineName="mysql",
        Tags=[{"Key": "Name", "Value": "Test Endpoint"}],
    )
    endpoint_2_arn = response["Endpoint"]["EndpointArn"]
    response = client.test_connection(
        ReplicationInstanceArn=replication_instance_2_arn, EndpointArn=endpoint_2_arn
    )
    response = client.describe_connections()
    assert len(response["Connections"]) == 2

    response = client.describe_endpoints()
    assert len(response["Endpoints"]) == 2
    client.delete_endpoint(EndpointArn=endpoint_1_arn)
    response = client.describe_endpoints()
    assert len(response["Endpoints"]) == 1

    # The connection should have been removed as its no longer valid
    response = client.describe_connections()
    assert len(response["Connections"]) == 1


@mock_aws
def test_describe_connections_filters():
    client = boto3.client("dms", region_name="eu-west-1")

    replication_instance_arn = ""
    endpoint_arn = ""
    for i in range(3):
        response = client.create_replication_instance(
            ReplicationInstanceIdentifier=f"test-instance-{i}",
            ReplicationInstanceClass="dms.t2.micro",
            EngineVersion="3.4.5",
        )
        replication_instance_arn = response["ReplicationInstance"][
            "ReplicationInstanceArn"
        ]
        response = client.create_endpoint(
            EndpointIdentifier=f"test-endpoint-{i}",
            EndpointType="source",
            EngineName="mysql",
        )
        endpoint_arn = response["Endpoint"]["EndpointArn"]
        response = client.test_connection(
            ReplicationInstanceArn=replication_instance_arn, EndpointArn=endpoint_arn
        )

    response = client.describe_connections()
    assert len(response["Connections"]) == 3

    replication_instance_filter = {
        "Name": "replication-instance-arn",
        "Values": [replication_instance_arn],
    }
    response = client.describe_connections(Filters=[replication_instance_filter])
    assert len(response["Connections"]) == 1

    endpoint_filter = {"Name": "endpoint-arn", "Values": [endpoint_arn]}
    response = client.describe_connections(Filters=[endpoint_filter])
    assert len(response["Connections"]) == 1

    response = client.describe_connections(
        Filters=[replication_instance_filter, endpoint_filter]
    )
    assert len(response["Connections"]) == 1

    invalid_replication_instance_filter = {
        "Name": "replication-instance-arn",
        "Values": ["invalid"],
    }
    response = client.describe_connections(
        Filters=[invalid_replication_instance_filter]
    )
    assert len(response["Connections"]) == 0

    invalid_endpoint_filter = {"Name": "endpoint-arn", "Values": ["invalid"]}
    response = client.describe_connections(Filters=[invalid_endpoint_filter])
    assert len(response["Connections"]) == 0
