import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID


@pytest.fixture(name="client")
@mock_aws
def get_rds_client():
    return boto3.client("rds", region_name="us-east-2")


@mock_aws
def test_create_db_shard_group(client):
    client.create_db_cluster(
        DBClusterIdentifier="test_db_cluster_identifier",
        Engine="aurora-postgresql",
        MasterUsername="admin",
        MasterUserPassword="root-password",
    )
    shard_group = client.create_db_shard_group(
        DBShardGroupIdentifier="shardgroup1",
        DBClusterIdentifier="test_db_cluster_identifier",
        MaxACU=100,
        MinACU=50,
        PubliclyAccessible=True,
        Tags=[{"Key": "Environment", "Value": "Test"}],
    )
    assert shard_group["DBShardGroupIdentifier"] == "shardgroup1"
    assert shard_group["DBClusterIdentifier"] == "test_db_cluster_identifier"
    assert (
        shard_group["DBShardGroupArn"]
        == f"arn:aws:rds:us-east-2:{DEFAULT_ACCOUNT_ID}:shard-group:shardgroup1"
    )


@mock_aws
def test_create_db_shard_group_duplicate(client):
    client.create_db_cluster(
        DBClusterIdentifier="test_db_cluster_identifier",
        Engine="aurora-postgresql",
        MasterUsername="admin",
        MasterUserPassword="root-password",
    )

    client.create_db_shard_group(
        DBShardGroupIdentifier="shardgroup1",
        DBClusterIdentifier="test_db_cluster_identifier",
        MaxACU=100,
        MinACU=50,
        PubliclyAccessible=True,
        Tags=[{"Key": "Environment", "Value": "Test"}],
    )

    with pytest.raises(ClientError) as ex:
        client.create_db_shard_group(
            DBShardGroupIdentifier="shardgroup1",
            DBClusterIdentifier="test_db_cluster_identifier",
            MaxACU=100,
            MinACU=50,
            PubliclyAccessible=True,
            Tags=[{"Key": "Environment", "Value": "Test"}],
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "DBShardGroupAlreadyExists"
    assert err["Message"] == "DB Shard Group shardgroup1 already exists."


@mock_aws
def test_shard_group_cluster_not_found(client):
    with pytest.raises(ClientError) as ex:
        client.create_db_shard_group(
            DBShardGroupIdentifier="shardgroup1",
            DBClusterIdentifier="test_db_cluster_identifier",
            MaxACU=100,
            MinACU=50,
            PubliclyAccessible=True,
            Tags=[{"Key": "Environment", "Value": "Test"}],
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "DBClusterNotFoundFault"
    assert err["Message"] == "DBCluster test_db_cluster_identifier not found."


@mock_aws
def test_shard_group_cluster_invalid_compute_redundancy(client):
    client.create_db_cluster(
        DBClusterIdentifier="test_db_cluster_identifier",
        Engine="aurora-postgresql",
        MasterUsername="admin",
        MasterUserPassword="root-password",
    )
    with pytest.raises(ClientError) as ex:
        client.create_db_shard_group(
            DBShardGroupIdentifier="shardgroup1",
            DBClusterIdentifier="test_db_cluster_identifier",
            ComputeRedundancy=3,
            MaxACU=100,
            MinACU=50,
            PubliclyAccessible=True,
            Tags=[{"Key": "Environment", "Value": "Test"}],
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert (
        err["Message"]
        == "Invalid ComputeRedundancy value: '3'. Valid values are 0 (no standby), 1 (1 standby AZ), 2 (2 standby AZs)."
    )


@mock_aws
def test_shard_group_cluster_invalid_max_min_acu(client):
    client.create_db_cluster(
        DBClusterIdentifier="test_db_cluster_identifier",
        Engine="aurora-postgresql",
        MasterUsername="admin",
        MasterUserPassword="root-password",
    )
    with pytest.raises(ClientError) as ex:
        client.create_db_shard_group(
            DBShardGroupIdentifier="shardgroup1",
            DBClusterIdentifier="test_db_cluster_identifier",
            ComputeRedundancy=1,
            MaxACU=0,
            MinACU=100,
            PubliclyAccessible=True,
            Tags=[{"Key": "Environment", "Value": "Test"}],
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert err["Message"] == "min_acu cannot be larger than max_acu"


@mock_aws
def test_describe_db_shard_group_initial(client):
    shard_groups = client.describe_db_shard_groups()
    assert len(shard_groups["DBShardGroups"]) == 0


@mock_aws
def test_describe_db_shard_group_non_existent(client):
    shard_groups = client.describe_db_shard_groups()
    assert len(shard_groups["DBShardGroups"]) == 0
    with pytest.raises(ClientError) as ex:
        client.describe_db_shard_groups(DBShardGroupIdentifier="shardgroup1")
    err = ex.value.response["Error"]
    assert err["Code"] == "DBShardGroupNotFound"
    assert err["Message"] == "DBShardGroup shardgroup1 not found."


@mock_aws
def test_describe_db_shard_group_after_creation(client):
    client.create_db_cluster(
        DBClusterIdentifier="test_db_cluster_identifier",
        Engine="aurora-postgresql",
        MasterUsername="admin",
        MasterUserPassword="root-password",
    )

    client.create_db_shard_group(
        DBShardGroupIdentifier="shardgroup1",
        DBClusterIdentifier="test_db_cluster_identifier",
        MaxACU=100,
        MinACU=50,
        PubliclyAccessible=True,
        Tags=[{"Key": "Environment", "Value": "Test"}],
    )

    shard_groups = client.describe_db_shard_groups(
        DBShardGroupIdentifier="shardgroup1"
    )["DBShardGroups"]
    assert len(shard_groups) == 1
    assert shard_groups[0]["DBShardGroupIdentifier"] == "shardgroup1"
    assert shard_groups[0]["DBClusterIdentifier"] == "test_db_cluster_identifier"
    assert (
        shard_groups[0]["DBShardGroupArn"]
        == f"arn:aws:rds:us-east-2:{DEFAULT_ACCOUNT_ID}:shard-group:shardgroup1"
    )


@mock_aws
def test_describe_db_shard_group_filter_by_cluster_id(client):
    client.create_db_cluster(
        DBClusterIdentifier="test_db_cluster_identifier",
        Engine="aurora-postgresql",
        MasterUsername="admin",
        MasterUserPassword="root-password",
    )
    client.create_db_shard_group(
        DBShardGroupIdentifier="shardgroup1",
        DBClusterIdentifier="test_db_cluster_identifier",
        MaxACU=100,
        MinACU=50,
        PubliclyAccessible=True,
        Tags=[{"Key": "Environment", "Value": "Test"}],
    )

    shard_groups = client.describe_db_shard_groups(
        DBShardGroupIdentifier="shardgroup1"
    )["DBShardGroups"]

    assert len(shard_groups) == 1
    assert shard_groups[0]["DBShardGroupIdentifier"] == "shardgroup1"
    assert shard_groups[0]["DBClusterIdentifier"] == "test_db_cluster_identifier"
    assert (
        shard_groups[0]["DBShardGroupArn"]
        == f"arn:aws:rds:us-east-2:{DEFAULT_ACCOUNT_ID}:shard-group:shardgroup1"
    )
