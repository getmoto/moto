import boto3

from moto import mock_aws


@mock_aws
def test_describe_db_cluster_parameters():
    client = boto3.client("rds", "us-east-2")

    resp = client.describe_db_cluster_parameters(DBClusterParameterGroupName="group")
    assert resp["Parameters"] == []
