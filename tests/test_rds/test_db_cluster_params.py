import boto3
import pytest

from moto import mock_aws


@mock_aws
def test_describe_db_cluster_parameters():
    client = boto3.client("rds", "us-east-2")
    # Create cluster
    client.create_db_cluster(
        DBClusterIdentifier="test-cluster",
        Engine="aurora-postgresql",
        MasterUsername="admin",
        MasterUserPassword="password",
        DBClusterParameterGroupName="group",
    )
    client.create_db_cluster_parameter_group(
        DBClusterParameterGroupName="group",
        DBParameterGroupFamily="aurora5.6",
        Description="Test group",
    )

    resp = client.describe_db_cluster_parameters(DBClusterParameterGroupName="group")
    assert resp["Parameters"] == []


@mock_aws
def test_modify_db_cluster_parameter_group():
    client = boto3.client("rds", "us-east-2")
    # Create cluster
    client.create_db_cluster(
        DBClusterIdentifier="test-cluster",
        Engine="aurora-postgresql",
        MasterUsername="admin",
        MasterUserPassword="password",
        DBClusterParameterGroupName="group",
    )
    client.create_db_cluster_parameter_group(
        DBClusterParameterGroupName="group",
        DBParameterGroupFamily="aurora5.6",
        Description="Test group",
    )

    client.modify_db_cluster_parameter_group(
        DBClusterParameterGroupName="group",
        Parameters=[
            {
                "ParameterName": "rds.force_ssl",
                "ParameterValue": "0",
                "ApplyMethod": "immediate",
            }
        ],
    )
    resp = client.describe_db_cluster_parameters(DBClusterParameterGroupName="group")
    assert resp["Parameters"][0]["ParameterName"] == "rds.force_ssl"
    assert resp["Parameters"][0]["ParameterValue"] == "0"
    assert resp["Parameters"][0]["ApplyMethod"] == "immediate"


@mock_aws
def test_describe_db_cluster_parameters_not_found():
    client = boto3.client("rds", "us-east-2")
    with pytest.raises(client.exceptions.DBParameterGroupNotFoundFault) as excinfo:
        client.describe_db_cluster_parameters(
            DBClusterParameterGroupName="nonexistent-group"
        )
    assert "DBClusterParameterGroup not found: nonexistent-group" in str(excinfo.value)
