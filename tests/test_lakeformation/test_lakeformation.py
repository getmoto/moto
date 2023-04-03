"""Unit tests for lakeformation-supported APIs."""
import boto3
import pytest

from botocore.exceptions import ClientError
from moto import mock_lakeformation
from moto.core import DEFAULT_ACCOUNT_ID

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


@mock_lakeformation
def test_lf_tags():
    client = boto3.client("lakeformation", region_name="eu-west-2")

    client.create_lf_tag(TagKey="tag1", TagValues=["1a", "1b"])
    client.create_lf_tag(TagKey="tag2", TagValues=["2a", "2b"])
    client.create_lf_tag(TagKey="tag3", TagValues=["3a", "3b"])

    resp = client.get_lf_tag(TagKey="tag1")
    assert resp["CatalogId"] == DEFAULT_ACCOUNT_ID
    assert resp["TagKey"] == "tag1"
    assert resp["TagValues"] == ["1a", "1b"]

    resp = client.list_lf_tags()
    assert len(resp["LFTags"]) == 3
    assert {
        "CatalogId": DEFAULT_ACCOUNT_ID,
        "TagKey": "tag1",
        "TagValues": ["1a", "1b"],
    } in resp["LFTags"]
    assert {
        "CatalogId": DEFAULT_ACCOUNT_ID,
        "TagKey": "tag2",
        "TagValues": ["2a", "2b"],
    } in resp["LFTags"]
    assert {
        "CatalogId": DEFAULT_ACCOUNT_ID,
        "TagKey": "tag3",
        "TagValues": ["3a", "3b"],
    } in resp["LFTags"]

    client.delete_lf_tag(TagKey="tag2")

    resp = client.list_lf_tags()
    assert len(resp["LFTags"]) == 2
    assert {
        "CatalogId": DEFAULT_ACCOUNT_ID,
        "TagKey": "tag1",
        "TagValues": ["1a", "1b"],
    } in resp["LFTags"]
    assert {
        "CatalogId": DEFAULT_ACCOUNT_ID,
        "TagKey": "tag3",
        "TagValues": ["3a", "3b"],
    } in resp["LFTags"]


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
