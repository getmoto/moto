import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws


@mock_aws
def test_create_db_cluster_parameter_group():
    client = boto3.client("docdb", region_name="us-east-1")
    resp = client.create_db_cluster_parameter_group(
        DBClusterParameterGroupName="my-docdb-params",
        DBParameterGroupFamily="docdb5.0",
        Description="DocDB params",
        Tags=[{"Key": "k1", "Value": "v1"}],
    )["DBClusterParameterGroup"]
    assert resp["DBClusterParameterGroupName"] == "my-docdb-params"
    assert resp["DBParameterGroupFamily"] == "docdb5.0"
    assert resp["Description"] == "DocDB params"
    assert resp["DBClusterParameterGroupArn"].endswith(":cluster-pg:my-docdb-params")

    groups = client.describe_db_cluster_parameter_groups(
        DBClusterParameterGroupName="my-docdb-params"
    )["DBClusterParameterGroups"]
    assert len(groups) == 1
    assert groups[0]["DBParameterGroupFamily"] == "docdb5.0"

    tags = client.list_tags_for_resource(
        ResourceName=resp["DBClusterParameterGroupArn"]
    )["TagList"]
    assert tags == [{"Key": "k1", "Value": "v1"}]


@mock_aws
def test_modify_db_cluster_parameter_group():
    client = boto3.client("docdb", region_name="us-east-1")
    client.create_db_cluster_parameter_group(
        DBClusterParameterGroupName="my-docdb-params",
        DBParameterGroupFamily="docdb5.0",
        Description="DocDB params",
    )
    resp = client.modify_db_cluster_parameter_group(
        DBClusterParameterGroupName="my-docdb-params",
        Parameters=[
            {
                "ParameterName": "tls",
                "ParameterValue": "disabled",
                "ApplyMethod": "pending-reboot",
            }
        ],
    )
    assert resp["DBClusterParameterGroupName"] == "my-docdb-params"

    params = client.describe_db_cluster_parameters(
        DBClusterParameterGroupName="my-docdb-params"
    )["Parameters"]
    assert len(params) == 1
    assert params[0]["ParameterName"] == "tls"
    assert params[0]["ParameterValue"] == "disabled"


@mock_aws
def test_create_db_cluster_with_parameter_group():
    client = boto3.client("docdb", region_name="us-east-1")
    client.create_db_cluster_parameter_group(
        DBClusterParameterGroupName="my-docdb-params",
        DBParameterGroupFamily="docdb5.0",
        Description="DocDB params",
    )
    cluster = client.create_db_cluster(
        DBClusterIdentifier="cluster-id",
        Engine="docdb",
        MasterUsername="root",
        MasterUserPassword="hunter2000",
        DBClusterParameterGroupName="my-docdb-params",
    )["DBCluster"]
    assert cluster["DBClusterParameterGroup"] == "my-docdb-params"


@mock_aws
def test_delete_db_cluster_parameter_group():
    client = boto3.client("docdb", region_name="us-east-1")
    client.create_db_cluster_parameter_group(
        DBClusterParameterGroupName="my-docdb-params",
        DBParameterGroupFamily="docdb5.0",
        Description="DocDB params",
    )
    client.delete_db_cluster_parameter_group(
        DBClusterParameterGroupName="my-docdb-params"
    )
    with pytest.raises(ClientError) as exc:
        client.describe_db_cluster_parameter_groups(
            DBClusterParameterGroupName="my-docdb-params"
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "DBParameterGroupNotFound"


@mock_aws
def test_reset_db_cluster_parameter_group():
    client = boto3.client("docdb", region_name="us-east-1")
    client.create_db_cluster_parameter_group(
        DBClusterParameterGroupName="my-docdb-params",
        DBParameterGroupFamily="docdb5.0",
        Description="DocDB params",
    )
    client.modify_db_cluster_parameter_group(
        DBClusterParameterGroupName="my-docdb-params",
        Parameters=[
            {"ParameterName": "tls", "ParameterValue": "disabled"},
            {"ParameterName": "audit_logs", "ParameterValue": "enabled"},
        ],
    )

    resp = client.reset_db_cluster_parameter_group(
        DBClusterParameterGroupName="my-docdb-params",
        Parameters=[{"ParameterName": "tls"}],
    )
    assert resp["DBClusterParameterGroupName"] == "my-docdb-params"
    params = client.describe_db_cluster_parameters(
        DBClusterParameterGroupName="my-docdb-params"
    )["Parameters"]
    assert [p["ParameterName"] for p in params] == ["audit_logs"]

    client.reset_db_cluster_parameter_group(
        DBClusterParameterGroupName="my-docdb-params", ResetAllParameters=True
    )
    params = client.describe_db_cluster_parameters(
        DBClusterParameterGroupName="my-docdb-params"
    )["Parameters"]
    assert params == []

    with pytest.raises(ClientError) as exc:
        client.reset_db_cluster_parameter_group(
            DBClusterParameterGroupName="unknown", ResetAllParameters=True
        )
    assert exc.value.response["Error"]["Code"] == "DBParameterGroupNotFound"
