import boto3
import pytest

from botocore.exceptions import ClientError
from moto import mock_rds
from moto.core import DEFAULT_ACCOUNT_ID


@mock_rds
def test_create_describe_delete():
    client = boto3.client("rds", "us-east-2")

    groups = client.describe_db_cluster_parameter_groups()["DBClusterParameterGroups"]
    assert len(groups) == 0

    group = client.create_db_cluster_parameter_group(
        DBClusterParameterGroupName="groupname",
        DBParameterGroupFamily="aurora5.6",
        Description="familia",
    )["DBClusterParameterGroup"]

    assert group["DBClusterParameterGroupName"] == "groupname"
    assert group["DBParameterGroupFamily"] == "aurora5.6"
    assert group["Description"] == "familia"
    assert (
        group["DBClusterParameterGroupArn"]
        == f"arn:aws:rds:us-east-2:{DEFAULT_ACCOUNT_ID}:cpg:groupname"
    )

    groups = client.describe_db_cluster_parameter_groups(
        DBClusterParameterGroupName="groupname",
    )["DBClusterParameterGroups"]

    assert len(groups) == 1
    assert groups[0]["DBClusterParameterGroupName"] == "groupname"
    assert groups[0]["DBParameterGroupFamily"] == "aurora5.6"
    assert groups[0]["Description"] == "familia"
    assert (
        groups[0]["DBClusterParameterGroupArn"]
        == f"arn:aws:rds:us-east-2:{DEFAULT_ACCOUNT_ID}:cpg:groupname"
    )

    client.delete_db_cluster_parameter_group(DBClusterParameterGroupName="groupname")

    groups = client.describe_db_cluster_parameter_groups()["DBClusterParameterGroups"]

    assert len(groups) == 0

    with pytest.raises(ClientError) as exc:
        client.describe_db_cluster_parameter_groups(
            DBClusterParameterGroupName="groupname",
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "DBParameterGroupNotFound"
    assert err["Message"] == "DBClusterParameterGroup not found: groupname"
