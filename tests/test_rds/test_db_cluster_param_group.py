import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID


@mock_aws
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
        == f"arn:aws:rds:us-east-2:{DEFAULT_ACCOUNT_ID}:cluster-pg:groupname"
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
        == f"arn:aws:rds:us-east-2:{DEFAULT_ACCOUNT_ID}:cluster-pg:groupname"
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


@mock_aws
def test_list_tags_for_resource():
    client = boto3.client("rds", "us-east-2")

    group = client.create_db_cluster_parameter_group(
        DBClusterParameterGroupName="groupname",
        DBParameterGroupFamily="aurora5.6",
        Description="familia",
        Tags=[{"Key": "environment", "Value": "test"}],
    )["DBClusterParameterGroup"]

    tags = client.list_tags_for_resource(
        ResourceName=group["DBClusterParameterGroupArn"]
    )

    assert {"Key": "environment", "Value": "test"} in tags["TagList"]


@mock_aws
def test_copy():
    client = boto3.client("rds", "us-east-2")

    source_group = client.create_db_cluster_parameter_group(
        DBClusterParameterGroupName="groupname",
        DBParameterGroupFamily="aurora5.6",
        Description="familia",
    )["DBClusterParameterGroup"]

    client.copy_db_cluster_parameter_group(
        SourceDBClusterParameterGroupIdentifier=source_group[
            "DBClusterParameterGroupArn"
        ],
        TargetDBClusterParameterGroupIdentifier="targetgroup",
        TargetDBClusterParameterGroupDescription="familia target",
    )

    target_group = client.describe_db_cluster_parameter_groups(
        DBClusterParameterGroupName="targetgroup",
    )["DBClusterParameterGroups"][0]

    assert target_group["DBParameterGroupFamily"] == "aurora5.6"
    assert target_group["Description"] == "familia target"


@mock_aws
def test_already_exists():
    client = boto3.client("rds", "us-east-2")

    source_group = client.create_db_cluster_parameter_group(
        DBClusterParameterGroupName="groupname",
        DBParameterGroupFamily="aurora5.6",
        Description="familia",
    )["DBClusterParameterGroup"]

    with pytest.raises(client.exceptions.DBParameterGroupAlreadyExistsFault):
        client.copy_db_cluster_parameter_group(
            SourceDBClusterParameterGroupIdentifier=source_group[
                "DBClusterParameterGroupName"
            ],
            TargetDBClusterParameterGroupIdentifier="groupname",
            TargetDBClusterParameterGroupDescription="familia target",
        )

    with pytest.raises(client.exceptions.DBParameterGroupAlreadyExistsFault):
        client.create_db_cluster_parameter_group(
            DBClusterParameterGroupName="groupname",
            DBParameterGroupFamily="aurora5.6",
            Description="familia",
        )


@mock_aws
def test_not_found():
    client = boto3.client("rds", "us-east-2")

    with pytest.raises(client.exceptions.DBParameterGroupNotFoundFault):
        client.delete_db_cluster_parameter_group(DBClusterParameterGroupName="nogroup")

    with pytest.raises(client.exceptions.DBParameterGroupNotFoundFault):
        client.copy_db_cluster_parameter_group(
            SourceDBClusterParameterGroupIdentifier="nogroup",
            TargetDBClusterParameterGroupIdentifier="targetgroup",
            TargetDBClusterParameterGroupDescription="familia target",
        )


@mock_aws
def test_create_validation():
    client = boto3.client("rds", "us-east-2")

    with pytest.raises(client.exceptions.ClientError) as exc:
        client.create_db_cluster_parameter_group(
            DBClusterParameterGroupName="groupname",
            DBParameterGroupFamily="",
            Description="familia",
        )
    error = exc.value.response["Error"]
    assert error["Code"] == "InvalidParameterValue"
    assert "DBParameterGroupFamily" in error["Message"]

    with pytest.raises(client.exceptions.ClientError) as exc:
        client.create_db_cluster_parameter_group(
            DBClusterParameterGroupName="groupname",
            DBParameterGroupFamily="aurora5.6",
            Description="",
        )
    error = exc.value.response["Error"]
    assert error["Code"] == "InvalidParameterValue"
    assert "Description" in error["Message"]
