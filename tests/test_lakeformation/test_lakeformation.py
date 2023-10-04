"""Unit tests for lakeformation-supported APIs."""
import boto3
import pytest

from botocore.exceptions import ClientError
from moto import mock_lakeformation

from . import lakeformation_aws_verified

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_lakeformation
def test_register_resource():
    client = boto3.client("lakeformation", region_name="us-east-2")
    resp = client.register_resource(
        ResourceArn="some arn",
    )

    del resp["ResponseMetadata"]
    assert resp == {}


@mock_lakeformation
def test_describe_resource():
    client = boto3.client("lakeformation", region_name="us-east-2")
    client.register_resource(ResourceArn="some arn", RoleArn="role arn")

    resp = client.describe_resource(ResourceArn="some arn")

    assert resp["ResourceInfo"] == {"ResourceArn": "some arn", "RoleArn": "role arn"}


@mock_lakeformation
def test_deregister_resource():
    client = boto3.client("lakeformation", region_name="us-east-2")
    client.register_resource(ResourceArn="some arn")
    client.deregister_resource(ResourceArn="some arn")

    with pytest.raises(ClientError) as exc:
        client.describe_resource(ResourceArn="some arn")
    err = exc.value.response["Error"]
    assert err["Code"] == "EntityNotFoundException"


@mock_lakeformation
def test_list_resources():
    client = boto3.client("lakeformation", region_name="us-east-2")

    resp = client.list_resources()
    assert resp["ResourceInfoList"] == []

    client.register_resource(ResourceArn="some arn")
    client.register_resource(ResourceArn="another arn")

    resp = client.list_resources()
    assert len(resp["ResourceInfoList"]) == 2


@mock_lakeformation
def test_data_lake_settings():
    client = boto3.client("lakeformation", region_name="us-east-2")
    resp = client.get_data_lake_settings()
    assert resp["DataLakeSettings"] == {
        "DataLakeAdmins": [],
        "CreateDatabaseDefaultPermissions": [
            {
                "Principal": {"DataLakePrincipalIdentifier": "IAM_ALLOWED_PRINCIPALS"},
                "Permissions": ["ALL"],
            }
        ],
        "CreateTableDefaultPermissions": [
            {
                "Principal": {"DataLakePrincipalIdentifier": "IAM_ALLOWED_PRINCIPALS"},
                "Permissions": ["ALL"],
            }
        ],
        "TrustedResourceOwners": [],
        "AllowExternalDataFiltering": False,
        "ExternalDataFilteringAllowList": [],
    }

    settings = {"DataLakeAdmins": [{"DataLakePrincipalIdentifier": "dlpi"}]}
    client.put_data_lake_settings(DataLakeSettings=settings)

    resp = client.get_data_lake_settings()
    assert resp["DataLakeSettings"] == settings


@mock_lakeformation
def test_list_permissions():
    client = boto3.client("lakeformation", region_name="eu-west-2")

    resp = client.grant_permissions(
        Principal={"DataLakePrincipalIdentifier": "asdf"},
        Resource={"Database": {"Name": "db"}},
        Permissions=["ALL"],
        PermissionsWithGrantOption=["SELECT"],
    )

    del resp["ResponseMetadata"]
    assert resp == {}

    # list all
    resp = client.list_permissions()
    assert resp["PrincipalResourcePermissions"] == [
        {
            "Principal": {"DataLakePrincipalIdentifier": "asdf"},
            "Resource": {"Database": {"Name": "db"}},
            "Permissions": ["ALL"],
            "PermissionsWithGrantOption": ["SELECT"],
        }
    ]


@mock_lakeformation
def test_revoke_permissions():
    client = boto3.client("lakeformation", region_name="eu-west-2")

    client.grant_permissions(
        Principal={"DataLakePrincipalIdentifier": "asdf"},
        Resource={"Database": {"Name": "db"}},
        Permissions=["SELECT", "ALTER", "DROP"],
        PermissionsWithGrantOption=["SELECT", "DROP"],
    )

    resp = client.revoke_permissions(
        Principal={"DataLakePrincipalIdentifier": "asdf"},
        Resource={"Database": {"Name": "db"}},
        Permissions=["DROP"],
    )

    del resp["ResponseMetadata"]
    assert resp == {}

    # list all
    resp = client.list_permissions()
    assert resp["PrincipalResourcePermissions"] == [
        {
            "Principal": {"DataLakePrincipalIdentifier": "asdf"},
            "Resource": {"Database": {"Name": "db"}},
            "Permissions": ["SELECT", "ALTER"],
            "PermissionsWithGrantOption": ["SELECT", "DROP"],
        }
    ]


@lakeformation_aws_verified
def test_lf_tags(
    bucket_name=None, db_name=None, table_name=None, column_name=None
):  # pylint: disable=unused-argument
    client = boto3.client("lakeformation", region_name="eu-west-2")
    sts = boto3.client("sts", "eu-west-2")
    account_id = sts.get_caller_identity()["Account"]

    client.create_lf_tag(TagKey="tag1", TagValues=["1a", "1b", "1c"])
    client.create_lf_tag(TagKey="tag2", TagValues=["2a", "2b"])
    client.create_lf_tag(TagKey="tag3", TagValues=["3a", "3b"])

    resp = client.get_lf_tag(TagKey="tag1")
    assert resp["CatalogId"] == account_id
    assert resp["TagKey"] == "tag1"
    assert resp["TagValues"] == ["1a", "1b", "1c"]

    client.update_lf_tag(TagKey="tag1", TagValuesToDelete=["1a", "1c"])

    tags = client.list_lf_tags()["LFTags"]
    assert set([x["CatalogId"] for x in tags]) == {account_id}
    tag_keys = [x["TagKey"] for x in tags]
    assert "tag1" in tag_keys
    assert "tag2" in tag_keys
    assert "tag3" in tag_keys

    assert [x for x in tags if x["TagKey"] == "tag1"][0]["TagValues"] == ["1b"]
    assert set([x for x in tags if x["TagKey"] == "tag2"][0]["TagValues"]) == {
        "2a",
        "2b",
    }
    assert set([x for x in tags if x["TagKey"] == "tag3"][0]["TagValues"]) == {
        "3a",
        "3b",
    }

    client.delete_lf_tag(TagKey="tag2")

    tags = client.list_lf_tags()["LFTags"]
    tag_keys = [x["TagKey"] for x in tags]
    assert "tag1" in tag_keys
    assert "tag3" in tag_keys
    assert "tag2" not in tag_keys

    client.delete_lf_tag(TagKey="tag1")
    client.delete_lf_tag(TagKey="tag3")


@mock_lakeformation
def test_list_data_cells_filter():
    client = boto3.client("lakeformation", region_name="eu-west-2")

    resp = client.list_data_cells_filter()
    assert resp["DataCellsFilters"] == []


@mock_lakeformation
def test_batch_revoke_permissions():
    client = boto3.client("lakeformation", region_name="eu-west-2")

    client.batch_grant_permissions(
        Entries=[
            {
                "Id": "id1",
                "Principal": {"DataLakePrincipalIdentifier": "id1"},
                "Resource": {"Database": {"Name": "db"}},
                "Permissions": ["SELECT", "ALTER", "DROP"],
                "PermissionsWithGrantOption": ["SELECT", "DROP"],
            },
            {
                "Id": "id2",
                "Principal": {"DataLakePrincipalIdentifier": "id2"},
                "Resource": {"Database": {"Name": "db"}},
                "Permissions": ["SELECT", "ALTER", "DROP"],
                "PermissionsWithGrantOption": ["SELECT", "DROP"],
            },
            {
                "Id": "id3",
                "Principal": {"DataLakePrincipalIdentifier": "id3"},
                "Resource": {"Database": {"Name": "db"}},
                "Permissions": ["SELECT", "ALTER", "DROP"],
                "PermissionsWithGrantOption": ["SELECT", "DROP"],
            },
        ]
    )

    resp = client.list_permissions()
    assert len(resp["PrincipalResourcePermissions"]) == 3

    client.batch_revoke_permissions(
        Entries=[
            {
                "Id": "id1",
                "Principal": {"DataLakePrincipalIdentifier": "id2"},
                "Resource": {"Database": {"Name": "db"}},
                "Permissions": ["SELECT", "ALTER", "DROP"],
                "PermissionsWithGrantOption": ["SELECT", "DROP"],
            },
            {
                "Id": "id2",
                "Principal": {"DataLakePrincipalIdentifier": "id3"},
                "Resource": {"Database": {"Name": "db"}},
                "Permissions": ["SELECT", "ALTER", "DROP"],
                "PermissionsWithGrantOption": ["SELECT", "DROP"],
            },
        ]
    )

    resp = client.list_permissions()
    assert len(resp["PrincipalResourcePermissions"]) == 1
