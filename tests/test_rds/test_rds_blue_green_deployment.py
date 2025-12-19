import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws

from . import DEFAULT_REGION
from .test_rds import (
    create_db_instance,
    create_subnet,
)
from .test_rds_clusters import create_db_cluster


@pytest.fixture(name="client")
@mock_aws
def get_rds_client():
    return boto3.client("rds", region_name=DEFAULT_REGION)


@mock_aws
def test_create_bluegreen_deployment_creates_a_green_db_instance(client):
    expected_target_engine_version = "17.3"
    expected_target_db_instance_class = "db.6g.xlarge"
    expected_target_allocated_storage = 999
    expected_db_parameter_group_name = "new_parameter_group"
    expected_target_iops = 5000
    expected_target_storage_type = "gp3"
    expected_target_storage_throughput = 6329

    subnet_id = create_subnet()
    subnet = client.create_db_subnet_group(
        DBSubnetGroupName="db_subnet1",
        DBSubnetGroupDescription="my db subnet",
        SubnetIds=[subnet_id],
        Tags=[{"Value": "bar", "Key": "foo"}, {"Value": "bar1", "Key": "foo1"}],
    )["DBSubnetGroup"]["DBSubnetGroupName"]

    instance = create_db_instance(
        DBInstanceIdentifier="FooBar",
        DBSubnetGroupName=subnet,
        MasterUsername="Bob",
        ManageMasterUserPassword=False,
    )
    client.create_db_parameter_group(
        DBParameterGroupName=expected_db_parameter_group_name,
        DBParameterGroupFamily="postgres",
        Description="Foobar",
    )

    response = client.create_blue_green_deployment(
        BlueGreenDeploymentName="FooBarBlueGreen",
        Source=instance["DBInstanceArn"],
        TargetEngineVersion=expected_target_engine_version,
        TargetDBInstanceClass=expected_target_db_instance_class,
        TargetAllocatedStorage=expected_target_allocated_storage,
        TargetDBParameterGroupName=expected_db_parameter_group_name,
        TargetIops=expected_target_iops,
        TargetStorageType=expected_target_storage_type,
        TargetStorageThroughput=expected_target_storage_throughput,
    )

    bluegreen_deployment_response = response["BlueGreenDeployment"]

    db_describe_response = client.describe_db_instances(
        DBInstanceIdentifier=bluegreen_deployment_response["Target"]
    )

    assert bluegreen_deployment_response is not None
    assert "bgd-" in bluegreen_deployment_response["BlueGreenDeploymentIdentifier"]
    assert bluegreen_deployment_response["BlueGreenDeploymentName"] == "FooBarBlueGreen"
    assert bluegreen_deployment_response["Source"] == instance["DBInstanceArn"]
    assert (
        bluegreen_deployment_response["Target"]
        == db_describe_response["DBInstances"][0]["DBInstanceArn"]
    )
    assert bluegreen_deployment_response["Status"] == "PROVISIONING"

    assert len(db_describe_response["DBInstances"]) > 0
    assert (
        db_describe_response["DBInstances"][0]["EngineVersion"]
        == expected_target_engine_version
    )
    assert (
        db_describe_response["DBInstances"][0]["DBInstanceClass"]
        == expected_target_db_instance_class
    )
    assert (
        db_describe_response["DBInstances"][0]["AllocatedStorage"]
        == expected_target_allocated_storage
    )
    assert (
        db_describe_response["DBInstances"][0]["DBParameterGroups"][0][
            "DBParameterGroupName"
        ]
        == expected_db_parameter_group_name
    )
    assert db_describe_response["DBInstances"][0]["Iops"] == expected_target_iops
    assert (
        db_describe_response["DBInstances"][0]["StorageType"]
        == expected_target_storage_type
    )
    assert (
        db_describe_response["DBInstances"][0]["StorageThroughput"]
        == expected_target_storage_throughput
    )
    assert (
        db_describe_response["DBInstances"][0]["DBSecurityGroups"]
        == instance["DBSecurityGroups"]
    )
    assert (
        db_describe_response["DBInstances"][0]["DBSubnetGroup"]["DBSubnetGroupName"]
        == instance["DBSubnetGroup"]["DBSubnetGroupName"]
    )
    assert (
        db_describe_response["DBInstances"][0]["OptionGroupMemberships"][0][
            "OptionGroupName"
        ]
        != instance["OptionGroupMemberships"][0]["OptionGroupName"]
    )
    assert db_describe_response["DBInstances"][0].get("MasterUserSecret") is None


@mock_aws
def test_create_bluegreen_deployment_creates_a_green_db_cluster(client):
    expected_target_engine_version = "17.3"
    expected_db_parameter_group_name = "new_parameter_group"
    expected_db_cluster_parameter_group_name = "new_cluster_parameter_group"

    subnet_id = create_subnet()
    subnet = client.create_db_subnet_group(
        DBSubnetGroupName="db_subnet1",
        DBSubnetGroupDescription="my db subnet",
        SubnetIds=[subnet_id],
        Tags=[{"Value": "bar", "Key": "foo"}, {"Value": "bar1", "Key": "foo1"}],
    )["DBSubnetGroup"]["DBSubnetGroupName"]

    create_db_cluster(
        DBClusterIdentifier="cluster-1",
        DBSubnetGroupName=subnet,
        MasterUsername="Bob",
        Engine="aurora-postgresql",
    )
    clustered_instances = []
    for i in range(3):
        clustered_instances.append(
            client.create_db_instance(
                DBInstanceIdentifier=f"test-instance-{i}",
                DBInstanceClass="db.m1.small",
                Engine="aurora-postgresql",
                DBClusterIdentifier="cluster-1",
                DBSubnetGroupName=subnet,
            )
        )
    cluster = client.describe_db_clusters(
        DBClusterIdentifier="cluster-1",
    )["DBClusters"][0]
    client.create_db_parameter_group(
        DBParameterGroupName=expected_db_parameter_group_name,
        DBParameterGroupFamily="postgres",
        Description="Foobar",
    )
    client.create_db_cluster_parameter_group(
        DBClusterParameterGroupName=expected_db_cluster_parameter_group_name,
        DBParameterGroupFamily="aurora-postgresql14",
        Description="FooBar",
    )

    response = client.create_blue_green_deployment(
        BlueGreenDeploymentName="FooBarBlueGreen",
        Source=cluster["DBClusterArn"],
        TargetEngineVersion=expected_target_engine_version,
        TargetDBParameterGroupName=expected_db_parameter_group_name,
        TargetDBClusterParameterGroupName=expected_db_cluster_parameter_group_name,
    )

    bluegreen_deployment_response = response["BlueGreenDeployment"]

    db_describe_response = client.describe_db_clusters(
        DBClusterIdentifier=bluegreen_deployment_response["Target"]
    )

    assert bluegreen_deployment_response is not None
    assert "bgd-" in bluegreen_deployment_response["BlueGreenDeploymentIdentifier"]
    assert bluegreen_deployment_response["BlueGreenDeploymentName"] == "FooBarBlueGreen"
    assert bluegreen_deployment_response["Source"] == cluster["DBClusterArn"]
    assert (
        bluegreen_deployment_response["Target"]
        == db_describe_response["DBClusters"][0]["DBClusterArn"]
    )
    assert bluegreen_deployment_response["Status"] == "PROVISIONING"

    assert len(db_describe_response["DBClusters"]) > 0
    assert (
        db_describe_response["DBClusters"][0]["EngineVersion"]
        == expected_target_engine_version
    )
    assert (
        db_describe_response["DBClusters"][0]["AllocatedStorage"]
        == cluster["AllocatedStorage"]
    )
    assert db_describe_response["DBClusters"][0].get("MasterUserSecret") is None
    assert (
        db_describe_response["DBClusters"][0]["DBClusterParameterGroup"]
        == expected_db_cluster_parameter_group_name
    )

    assert len(db_describe_response["DBClusters"][0]["DBClusterMembers"]) == len(
        cluster["DBClusterMembers"]
    )
    for index, member in enumerate(
        db_describe_response["DBClusters"][0]["DBClusterMembers"]
    ):
        member_response = client.describe_db_instances(
            DBInstanceIdentifier=member["DBInstanceIdentifier"]
        )

        assert (
            member_response["DBInstances"][0]["DBSubnetGroup"]["DBSubnetGroupName"]
            == clustered_instances[index]["DBInstance"]["DBSubnetGroup"][
                "DBSubnetGroupName"
            ]
        )


@mock_aws
def test_create_blue_green_deployment_db_instance_with_managed_master_password(client):
    instance = create_db_instance(
        DBInstanceIdentifier="FooBar",
        MasterUsername="Bob",
        ManageMasterUserPassword=True,
    )

    source_arn = instance["DBInstanceArn"]

    with pytest.raises(ClientError) as exc:
        client.create_blue_green_deployment(
            BlueGreenDeploymentName="FooBarBlueGreen",
            Source=source_arn,
        )

    err = exc.value.response["Error"]
    assert err["Code"] == "SourceDatabaseNotSupportedFault"
    assert (
        err["Message"]
        == f"The source DB instance {source_arn} isn't supported for a blue/green deployment."
    )


@mock_aws
def test_create_blue_green_deployment_rds_cluster_after_removing_managed_master_password(
    client,
):
    instance = create_db_instance(
        DBInstanceIdentifier="FooBar",
        MasterUsername="Bob",
        ManageMasterUserPassword=True,
    )

    source_arn = instance["DBInstanceArn"]

    client.modify_db_instance(
        DBInstanceIdentifier="FooBar",
        MasterUserPassword="myverysecretPassword",
        ManageMasterUserPassword=False,
    )

    blue_green_response = client.create_blue_green_deployment(
        BlueGreenDeploymentName="FooBarBlueGreen", Source=source_arn
    )

    assert (
        blue_green_response["BlueGreenDeployment"]["BlueGreenDeploymentIdentifier"]
        is not None
    )
    assert blue_green_response["BlueGreenDeployment"]["Target"] is not None
    assert blue_green_response["BlueGreenDeployment"]["Source"] == source_arn


@mock_aws
def test_create_blue_green_deployment_rds_cluster_with_managed_master_password(client):
    create_db_cluster(
        DBClusterIdentifier="cluster-1",
        MasterUsername="Bob",
        ManageMasterUserPassword=True,
        Engine="aurora-postgresql",
    )
    clustered_instances = []
    for i in range(3):
        clustered_instances.append(
            client.create_db_instance(
                DBInstanceIdentifier=f"test-instance-{i}",
                DBInstanceClass="db.m1.small",
                Engine="aurora-postgresql",
                DBClusterIdentifier="cluster-1",
            )
        )
    cluster = client.describe_db_clusters(
        DBClusterIdentifier="cluster-1",
    )["DBClusters"][0]

    source_arn = cluster["DBClusterArn"]

    with pytest.raises(ClientError) as exc:
        client.create_blue_green_deployment(
            BlueGreenDeploymentName="FooBarBlueGreen",
            Source=source_arn,
        )

    err = exc.value.response["Error"]
    assert err["Code"] == "SourceClusterNotSupportedFault"
    assert (
        err["Message"]
        == f"The source DB cluster {source_arn} isn't supported for a blue/green deployment."
    )


@mock_aws
def test_create_blue_green_deployment_error_if_source_db_instance_not_found(client):
    with pytest.raises(ClientError) as ex:
        client.create_blue_green_deployment(
            BlueGreenDeploymentName="FooBarBlueGreen",
            Source="arn:rds:123456789012:us-east-1:db:not_an_arn",
        )

    err = ex.value.response["Error"]
    assert err["Code"] == "DBInstanceNotFound"
    assert (
        err["Message"]
        == "DBInstance arn:rds:123456789012:us-east-1:db:not_an_arn not found."
    )


@mock_aws
def test_create_blue_green_deployment_error_if_source_rds_cluster_not_found(client):
    with pytest.raises(ClientError) as ex:
        client.create_blue_green_deployment(
            BlueGreenDeploymentName="FooBarBlueGreen",
            Source="arn:rds:123456789012:us-east-1:cluster:not_an_arn",
        )

    err = ex.value.response["Error"]
    assert err["Code"] == "DBClusterNotFoundFault"
    assert (
        err["Message"]
        == "DBCluster arn:rds:123456789012:us-east-1:cluster:not_an_arn not found."
    )


@mock_aws
def test_create_blue_green_deployment_with_duplicate_name(client):
    bluegreen_name = "FooBarBlueGreen"
    instance = create_db_instance(
        DBInstanceIdentifier="FooBar",
    )

    response = client.create_blue_green_deployment(
        BlueGreenDeploymentName=bluegreen_name,
        Source=instance["DBInstanceArn"],
    )

    with pytest.raises(ClientError) as ex:
        client.create_blue_green_deployment(
            BlueGreenDeploymentName=bluegreen_name,
            Source=instance["DBInstanceArn"],
        )

    error = ex.value.response["Error"]

    assert response["BlueGreenDeployment"]["BlueGreenDeploymentName"] == bluegreen_name
    assert error["Code"] == "BlueGreenDeploymentAlreadyExistsFault"
    assert (
        error["Message"]
        == "A blue/green deployment with the specified name FooBarBlueGreen already exists."
    )


@mock_aws
def test_describe_bluegreen_deployments_db_instance_with_filters(client):
    bg_name = "bluegreen-deployment-1"
    instance = create_db_instance(
        DBInstanceIdentifier="FooBar",
    )

    create_response = client.create_blue_green_deployment(
        BlueGreenDeploymentName=bg_name,
        Source=instance["DBInstanceArn"],
    )

    describe_response = client.describe_blue_green_deployments(
        BlueGreenDeploymentIdentifier=create_response["BlueGreenDeployment"][
            "BlueGreenDeploymentIdentifier"
        ]
    )

    describe_with_filters_response = client.describe_blue_green_deployments(
        Filters=[
            {"Name": "blue-green-deployment-name", "Values": [bg_name]},
            {"Name": "source", "Values": [instance["DBInstanceArn"]]},
        ]
    )

    update_status_from_create_blue_green_response(
        create_response["BlueGreenDeployment"]
    )

    assert (
        describe_response["BlueGreenDeployments"][0]["Tasks"][0]["Status"]
        == "COMPLETED"
    )

    assert (
        describe_response["BlueGreenDeployments"][0]
        == create_response["BlueGreenDeployment"]
    )
    assert len(describe_with_filters_response["BlueGreenDeployments"]) > 0
    assert (
        describe_with_filters_response["BlueGreenDeployments"][0]
        == describe_response["BlueGreenDeployments"][0]
    )


@mock_aws
def test_describe_bluegreen_deployments_db_cluster_with_filters(client):
    bg_name = "bluegreen-deployment-1"
    create_db_cluster(
        DBClusterIdentifier="cluster-1",
    )

    cluster = client.describe_db_clusters(
        DBClusterIdentifier="cluster-1",
    )["DBClusters"][0]

    create_response = client.create_blue_green_deployment(
        BlueGreenDeploymentName=bg_name,
        Source=cluster["DBClusterArn"],
    )

    describe_response = client.describe_blue_green_deployments(
        BlueGreenDeploymentIdentifier=create_response["BlueGreenDeployment"][
            "BlueGreenDeploymentIdentifier"
        ]
    )

    describe_with_filters_response = client.describe_blue_green_deployments(
        Filters=[
            {"Name": "blue-green-deployment-name", "Values": [bg_name]},
            {"Name": "source", "Values": [cluster["DBClusterArn"]]},
        ]
    )

    update_status_from_create_blue_green_response(
        create_response["BlueGreenDeployment"]
    )

    assert (
        describe_response["BlueGreenDeployments"][0]["Tasks"][0]["Status"]
        == "COMPLETED"
    )

    assert (
        describe_response["BlueGreenDeployments"][0]
        == create_response["BlueGreenDeployment"]
    )
    assert len(describe_with_filters_response["BlueGreenDeployments"]) > 0
    assert (
        describe_with_filters_response["BlueGreenDeployments"][0]
        == create_response["BlueGreenDeployment"]
    )


@mock_aws
def test_describe_bluegreen_deployments_with_no_hits(client):
    with pytest.raises(ClientError) as ex:
        client.describe_blue_green_deployments(
            BlueGreenDeploymentIdentifier="red-yellow"
        )

    filter_response = client.describe_blue_green_deployments(
        Filters=[{"Name": "source", "Values": ["no-real-arn"]}]
    )

    error = ex.value.response["Error"]

    assert error["Code"] == "BlueGreenDeploymentNotFoundFault"
    assert len(filter_response["BlueGreenDeployments"]) == 0


@mock_aws
def test_switchover_blue_green_deployment_switches_db_instances(client):
    bg_name = "bluegreen-deployment-1"
    instance = create_db_instance(
        DBInstanceIdentifier="FooBar",
    )

    create_response = client.create_blue_green_deployment(
        BlueGreenDeploymentName=bg_name,
        Source=instance["DBInstanceArn"],
    )

    switchover_response = client.switchover_blue_green_deployment(
        BlueGreenDeploymentIdentifier=create_response["BlueGreenDeployment"][
            "BlueGreenDeploymentIdentifier"
        ]
    )

    describe_response = client.describe_blue_green_deployments(
        BlueGreenDeploymentIdentifier=create_response["BlueGreenDeployment"][
            "BlueGreenDeploymentIdentifier"
        ]
    )

    describe_target_instance = client.describe_db_instances(
        DBInstanceIdentifier=describe_response["BlueGreenDeployments"][0]["Target"]
    )

    assert (
        switchover_response["BlueGreenDeployment"]["Status"] == "SWITCHOVER_IN_PROGRESS"
    )
    assert (
        switchover_response["BlueGreenDeployment"]["Source"]
        == instance["DBInstanceArn"]
    )
    assert "green" in switchover_response["BlueGreenDeployment"]["Target"]

    assert (
        describe_response["BlueGreenDeployments"][0]["Status"] == "SWITCHOVER_COMPLETED"
    )
    assert "old" in describe_response["BlueGreenDeployments"][0]["Source"]
    assert (
        describe_response["BlueGreenDeployments"][0]["Target"].split(":")[-1]
        == instance["DBInstanceIdentifier"]
    )
    assert (
        describe_target_instance["DBInstances"][0]["Endpoint"] == instance["Endpoint"]
    )


@mock_aws
def test_switchover_blue_green_deployment_switches_rds_clusters(client):
    bg_name = "bluegreen-deployment-1"
    create_db_cluster(
        DBClusterIdentifier="cluster-1",
    )
    cluster = client.describe_db_clusters(
        DBClusterIdentifier="cluster-1",
    )["DBClusters"][0]

    create_response = client.create_blue_green_deployment(
        BlueGreenDeploymentName=bg_name,
        Source=cluster["DBClusterArn"],
    )

    switchover_response = client.switchover_blue_green_deployment(
        BlueGreenDeploymentIdentifier=create_response["BlueGreenDeployment"][
            "BlueGreenDeploymentIdentifier"
        ]
    )

    describe_response = client.describe_blue_green_deployments(
        BlueGreenDeploymentIdentifier=create_response["BlueGreenDeployment"][
            "BlueGreenDeploymentIdentifier"
        ]
    )

    describe_target_instance = client.describe_db_clusters(
        DBClusterIdentifier=describe_response["BlueGreenDeployments"][0]["Target"]
    )

    assert (
        switchover_response["BlueGreenDeployment"]["Status"] == "SWITCHOVER_IN_PROGRESS"
    )
    assert (
        switchover_response["BlueGreenDeployment"]["Source"] == cluster["DBClusterArn"]
    )
    assert "green" in switchover_response["BlueGreenDeployment"]["Target"]

    assert (
        describe_response["BlueGreenDeployments"][0]["Status"] == "SWITCHOVER_COMPLETED"
    )
    assert "old" in describe_response["BlueGreenDeployments"][0]["Source"]
    assert (
        describe_response["BlueGreenDeployments"][0]["Target"].split(":")[-1]
        == cluster["DBClusterIdentifier"]
    )
    assert (
        describe_target_instance["DBClusters"][0]["Endpoint"].split(".")[0]
        == cluster["Endpoint"].split(".")[0]
    )


@mock_aws
def test_switchover_after_successful_switchover_blue_green_deployment(client):
    bg_name = "bluegreen-deployment-1"
    instance = create_db_instance(
        DBInstanceIdentifier="FooBar",
    )

    create_response = client.create_blue_green_deployment(
        BlueGreenDeploymentName=bg_name,
        Source=instance["DBInstanceArn"],
    )

    client.switchover_blue_green_deployment(
        BlueGreenDeploymentIdentifier=create_response["BlueGreenDeployment"][
            "BlueGreenDeploymentIdentifier"
        ]
    )

    with pytest.raises(ClientError) as exc:
        client.switchover_blue_green_deployment(
            BlueGreenDeploymentIdentifier=create_response["BlueGreenDeployment"][
                "BlueGreenDeploymentIdentifier"
            ]
        )

    error = exc.value.response["Error"]
    assert error["Code"] == "InvalidBlueGreenDeploymentStateFault"


@mock_aws
@pytest.mark.parametrize(
    "options",
    [
        pytest.param(
            {"with_switchover": False, "delete_target": True},
            id="before_switchover_with_delete_target",
        ),
        pytest.param(
            {"with_switchover": False, "delete_target": False},
            id="before_switchover_without_delete_target",
        ),
        pytest.param(
            {"with_switchover": True, "delete_target": True},
            id="after_switchover_with_delete_target",
        ),
    ],
)
def test_delete_blue_green_deployment_with_source_db_instance(client, options):
    bg_name = "bluegreen-deployment-1"

    instance = create_db_instance(
        DBInstanceIdentifier="FooBar",
    )

    create_response = client.create_blue_green_deployment(
        BlueGreenDeploymentName=bg_name,
        Source=instance["DBInstanceArn"],
    )

    if options["with_switchover"]:
        client.switchover_blue_green_deployment(
            BlueGreenDeploymentIdentifier=create_response["BlueGreenDeployment"][
                "BlueGreenDeploymentIdentifier"
            ]
        )

    delete_response = client.delete_blue_green_deployment(
        BlueGreenDeploymentIdentifier=create_response["BlueGreenDeployment"][
            "BlueGreenDeploymentIdentifier"
        ],
        DeleteTarget=options["delete_target"],
    )

    describe_response = client.describe_blue_green_deployments(
        Filters=[{"Name": "blue-green-deployment-name", "Values": [bg_name]}]
    )

    describe_source_instance = client.describe_db_instances(
        DBInstanceIdentifier=delete_response["BlueGreenDeployment"]["Source"]
    )

    describe_target_instance = client.describe_db_instances(
        Filters=[
            {
                "Name": "db-instance-id",
                "Values": [delete_response["BlueGreenDeployment"]["Target"]],
            }
        ]
    )

    assert delete_response["BlueGreenDeployment"]["Status"] == "DELETING"
    assert len(describe_response["BlueGreenDeployments"]) == 0
    assert len(describe_source_instance["DBInstances"]) == 1
    if options["delete_target"] and not options["with_switchover"]:
        assert len(describe_target_instance["DBInstances"]) == 0
    else:
        assert len(describe_target_instance["DBInstances"]) == 1


@mock_aws
def test_delete_blue_green_deployment_when_it_does_not_exist(client):
    with pytest.raises(ClientError) as exc:
        client.delete_blue_green_deployment(
            BlueGreenDeploymentIdentifier="DoesNotExist"
        )

    error = exc.value.response["Error"]
    assert error["Code"] == "BlueGreenDeploymentNotFoundFault"


@mock_aws
@pytest.mark.parametrize(
    "options",
    [
        pytest.param(
            {"with_switchover": False, "delete_target": True},
            id="before_switchover_with_delete_target",
        ),
        pytest.param(
            {"with_switchover": False, "delete_target": False},
            id="before_switchover_without_delete_target",
        ),
        pytest.param(
            {"with_switchover": True, "delete_target": True},
            id="after_switchover_with_delete_target",
        ),
    ],
)
def test_delete_blue_green_deployment_with_source_db_cluster(client, options):
    bg_name = "bluegreen-deployment-1"

    create_db_cluster(
        DBClusterIdentifier="cluster-1",
        Engine="aurora-postgresql",
    )
    clustered_instances = []
    for i in range(3):
        clustered_instances.append(
            client.create_db_instance(
                DBInstanceIdentifier=f"test-instance-{i}",
                DBClusterIdentifier="cluster-1",
                DBInstanceClass="db.m1.small",
                Engine="aurora-postgresql",
            )
        )
    cluster = client.describe_db_clusters(
        DBClusterIdentifier="cluster-1",
    )["DBClusters"][0]

    create_response = client.create_blue_green_deployment(
        BlueGreenDeploymentName=bg_name,
        Source=cluster["DBClusterArn"],
    )

    if options["with_switchover"]:
        client.switchover_blue_green_deployment(
            BlueGreenDeploymentIdentifier=create_response["BlueGreenDeployment"][
                "BlueGreenDeploymentIdentifier"
            ]
        )

    delete_response = client.delete_blue_green_deployment(
        BlueGreenDeploymentIdentifier=create_response["BlueGreenDeployment"][
            "BlueGreenDeploymentIdentifier"
        ],
        DeleteTarget=options["delete_target"],
    )

    describe_response = client.describe_blue_green_deployments(
        Filters=[{"Name": "blue-green-deployment-name", "Values": [bg_name]}]
    )

    describe_source_cluster = client.describe_db_clusters(
        DBClusterIdentifier=delete_response["BlueGreenDeployment"]["Source"]
    )

    describe_target_cluster = client.describe_db_clusters(
        Filters=[
            {
                "Name": "db-cluster-id",
                "Values": [delete_response["BlueGreenDeployment"]["Target"]],
            }
        ]
    )

    assert delete_response["BlueGreenDeployment"]["Status"] == "DELETING"
    assert len(describe_response["BlueGreenDeployments"]) == 0
    assert len(describe_source_cluster["DBClusters"]) == 1
    if options["delete_target"] and not options["with_switchover"]:
        assert len(describe_target_cluster["DBClusters"]) == 0
    else:
        assert len(describe_target_cluster["DBClusters"]) == 1


def update_status_from_create_blue_green_response(bg_response: dict) -> None:
    bg_response["Status"] = "AVAILABLE"

    for details in bg_response["SwitchoverDetails"]:
        details["Status"] = "AVAILABLE"
    for task in bg_response["Tasks"]:
        task["Status"] = "COMPLETED"
