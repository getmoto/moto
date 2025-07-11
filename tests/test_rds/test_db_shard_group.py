import boto3

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID


@mock_aws
def test_create_db_shard_group():
    client = boto3.client("rds", "us-east-2")

    shard_group = client.create_db_shard_group(
        DBShardGroupIdentifier="shardgroup1",
        DBClusterIdentifier="cluster1",
        MaxACU=100,
        MinACU=50,
        PubliclyAccessible=True,
        Tags=[{"Key": "Environment", "Value": "Test"}],
    )

    assert shard_group["DBShardGroupIdentifier"] == "shardgroup1"
    assert shard_group["DBClusterIdentifier"] == "cluster1"
    assert (
        shard_group["DBShardGroupArn"]
        == f"arn:aws:rds:us-east-2:{DEFAULT_ACCOUNT_ID}:shard-group:shardgroup1"
    )


@mock_aws
def test_describe_db_shard_group():
    client = boto3.client("rds", "us-east-2")

    client.create_db_shard_group(
        DBShardGroupIdentifier="shardgroup1",
        DBClusterIdentifier="cluster1",
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
    assert shard_groups[0]["DBClusterIdentifier"] == "cluster1"
    assert (
        shard_groups[0]["DBShardGroupArn"]
        == f"arn:aws:rds:us-east-2:{DEFAULT_ACCOUNT_ID}:shard-group:shardgroup1"
    )
