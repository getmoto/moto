"""Unit tests for lakeformation-supported APIs."""

from typing import Dict, Optional

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_aws
def test_register_resource():
    client = boto3.client("lakeformation", region_name="us-east-2")
    resp = client.register_resource(ResourceArn="some arn", RoleArn="another arn")

    del resp["ResponseMetadata"]
    assert resp == {}
    with pytest.raises(client.exceptions.AlreadyExistsException):
        client.register_resource(ResourceArn="some arn", RoleArn="another arn")


@mock_aws
def test_describe_resource():
    client = boto3.client("lakeformation", region_name="us-east-2")
    client.register_resource(ResourceArn="some arn", RoleArn="role arn")

    resp = client.describe_resource(ResourceArn="some arn")

    assert resp["ResourceInfo"] == {"ResourceArn": "some arn", "RoleArn": "role arn"}


@mock_aws
def test_deregister_resource():
    client = boto3.client("lakeformation", region_name="us-east-2")
    client.register_resource(ResourceArn="some arn")
    client.deregister_resource(ResourceArn="some arn")

    with pytest.raises(ClientError) as exc:
        client.describe_resource(ResourceArn="some arn")
    err = exc.value.response["Error"]
    assert err["Code"] == "EntityNotFoundException"

    with pytest.raises(ClientError) as exc:
        client.deregister_resource(ResourceArn="some arn")
    err = exc.value.response["Error"]
    assert err["Code"] == "EntityNotFoundException"


@mock_aws
def test_list_resources():
    client = boto3.client("lakeformation", region_name="us-east-2")

    resp = client.list_resources()
    assert resp["ResourceInfoList"] == []

    client.register_resource(ResourceArn="some arn")
    client.register_resource(ResourceArn="another arn")

    resp = client.list_resources()
    assert len(resp["ResourceInfoList"]) == 2


@mock_aws
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


@mock_aws
def test_grant_permissions():
    client = boto3.client("lakeformation", region_name="us-east-2")

    resp = client.grant_permissions(
        Principal={"DataLakePrincipalIdentifier": "asdf"},
        Resource={"Database": {"Name": "db"}},
        Permissions=["ALL"],
    )
    del resp["ResponseMetadata"]
    assert resp == {}
    resp = client.list_permissions()
    assert resp["PrincipalResourcePermissions"] == [
        {
            "Principal": {"DataLakePrincipalIdentifier": "asdf"},
            "Resource": {"Database": {"Name": "db"}},
            "Permissions": ["ALL"],
            "PermissionsWithGrantOption": [],
        }
    ]


@mock_aws
def test_grant_permissions_idempotent():
    client = boto3.client("lakeformation", region_name="us-east-2")

    for _ in range(2):
        resp = client.grant_permissions(
            Principal={"DataLakePrincipalIdentifier": "asdf"},
            Resource={"Database": {"Name": "db"}},
            Permissions=["ALL"],
        )
        del resp["ResponseMetadata"]
        assert resp == {}
    resp = client.list_permissions()
    assert resp["PrincipalResourcePermissions"] == [
        {
            "Principal": {"DataLakePrincipalIdentifier": "asdf"},
            "Resource": {"Database": {"Name": "db"}},
            "Permissions": ["ALL"],
            "PermissionsWithGrantOption": [],
        }
    ]


@mock_aws
def test_grant_permissions_staggered():
    client = boto3.client("lakeformation", region_name="us-east-2")
    client.grant_permissions(
        Principal={"DataLakePrincipalIdentifier": "asdf"},
        Resource={"Database": {"Name": "db"}},
        Permissions=["DESCRIBE"],
    )
    client.grant_permissions(
        Principal={"DataLakePrincipalIdentifier": "asdf"},
        Resource={"Database": {"Name": "db"}},
        Permissions=["CREATE_TABLE"],
    )

    resp = client.list_permissions()
    assert len(resp["PrincipalResourcePermissions"]) == 1
    assert set(resp["PrincipalResourcePermissions"][0]["Permissions"]) == set(
        ["DESCRIBE", "CREATE_TABLE"]
    )


@mock_aws
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


@mock_aws
def test_list_permissions_invalid_input():
    client = boto3.client("lakeformation", region_name="eu-west-2")

    client.grant_permissions(
        Principal={"DataLakePrincipalIdentifier": "asdf"},
        Resource={"Database": {"Name": "db"}},
        Permissions=["ALL"],
        PermissionsWithGrantOption=["SELECT"],
    )

    with pytest.raises(client.exceptions.InvalidInputException):
        client.list_permissions(Principal={"DataLakePrincipalIdentifier": "asdf"})

    with pytest.raises(client.exceptions.InvalidInputException):
        client.list_permissions(Resource={})


def grant_table_permissions(
    client: boto3.client, catalog_id: str, principal: str, db: str, table: str
):
    client.grant_permissions(
        CatalogId=catalog_id,
        Principal={"DataLakePrincipalIdentifier": principal},
        Resource={
            "Table": {
                "DatabaseName": db,
                "Name": table,
                "CatalogId": catalog_id,
                "TableWildcard": {},
            }
        },
        Permissions=["ALL"],
        PermissionsWithGrantOption=["SELECT"],
    )


def grant_db_permissions(
    client: boto3.client, catalog_id: str, principal: str, db: str
):
    client.grant_permissions(
        CatalogId=catalog_id,
        Principal={"DataLakePrincipalIdentifier": principal},
        Resource={"Database": {"Name": db, "CatalogId": catalog_id}},
        Permissions=["ALL"],
        PermissionsWithGrantOption=["SELECT"],
    )


def grant_catalog_permissions(client: boto3.client, catalog_id: str, principal: str):
    client.grant_permissions(
        CatalogId=catalog_id,
        Principal={"DataLakePrincipalIdentifier": principal},
        Resource={"Catalog": {}},
        Permissions=["CREATE_DATABASE"],
        PermissionsWithGrantOption=[],
    )


def grant_data_location_permissions(
    client: boto3.client, resource_arn: str, catalog_id: str, principal: str
):
    client.grant_permissions(
        CatalogId=catalog_id,
        Principal={"DataLakePrincipalIdentifier": principal},
        Resource={"DataLocation": {"ResourceArn": resource_arn}},
        Permissions=["DATA_LOCATION_ACCESS"],
        PermissionsWithGrantOption=[],
    )


def db_response(principal: str, catalog_id: str, db: str) -> Dict:
    return {
        "Principal": {"DataLakePrincipalIdentifier": principal},
        "Resource": {
            "Database": {
                "CatalogId": catalog_id,
                "Name": db,
            }
        },
        "Permissions": ["ALL"],
        "PermissionsWithGrantOption": ["SELECT"],
    }


def table_response(principal: str, catalog_id: str, db: str, table: str) -> Dict:
    return {
        "Principal": {"DataLakePrincipalIdentifier": principal},
        "Resource": {
            "Table": {
                "CatalogId": catalog_id,
                "DatabaseName": db,
                "Name": table,
                "TableWildcard": {},
            }
        },
        "Permissions": ["ALL"],
        "PermissionsWithGrantOption": ["SELECT"],
    }


def catalog_response(principal: str) -> Dict:
    return {
        "Principal": {"DataLakePrincipalIdentifier": principal},
        "Resource": {"Catalog": {}},
        "Permissions": ["CREATE_DATABASE"],
        "PermissionsWithGrantOption": [],
    }


def data_location_response(
    principal: str, resource_arn: str, catalog_id: Optional[str] = None
) -> Dict:
    response = {
        "Principal": {"DataLakePrincipalIdentifier": principal},
        "Resource": {"DataLocation": {"ResourceArn": resource_arn}},
        "Permissions": ["DATA_LOCATION_ACCESS"],
        "PermissionsWithGrantOption": [],
    }
    if catalog_id is not None:
        response["Resource"]["CatalogId"] = catalog_id
    return response


@mock_aws
def test_list_permissions_filtered_for_catalog_id():
    client = boto3.client("lakeformation", region_name="eu-west-2")
    catalog_id_1 = "000000000000"
    catalog_id_2 = "000000000001"
    principal_1 = "principal_1"
    principal_2 = "principal_2"

    grant_catalog_permissions(
        client=client, catalog_id=catalog_id_1, principal=principal_1
    )
    grant_catalog_permissions(
        client=client, catalog_id=catalog_id_2, principal=principal_2
    )

    permissions = client.list_permissions(CatalogId=catalog_id_1)[
        "PrincipalResourcePermissions"
    ]
    assert permissions == [catalog_response(principal=principal_1)]

    permissions = client.list_permissions(CatalogId=catalog_id_2)[
        "PrincipalResourcePermissions"
    ]
    assert permissions == [catalog_response(principal=principal_2)]


@mock_aws
def test_list_permissions_filtered_for_resource_type():
    client = boto3.client("lakeformation", region_name="eu-west-2")
    catalog_id = "000000000000"
    principal_1 = "principal_1"
    db_1 = "db_1"
    table_1 = "table_1"

    grant_db_permissions(
        client=client, catalog_id=catalog_id, principal=principal_1, db=db_1
    )
    grant_table_permissions(
        client=client,
        catalog_id=catalog_id,
        principal=principal_1,
        db=db_1,
        table=table_1,
    )
    grant_catalog_permissions(
        client=client, catalog_id=catalog_id, principal=principal_1
    )

    res = client.list_permissions(CatalogId=catalog_id, ResourceType="DATABASE")
    assert res["PrincipalResourcePermissions"] == [
        db_response(principal=principal_1, catalog_id=catalog_id, db=db_1),
    ]

    res = client.list_permissions(CatalogId=catalog_id, ResourceType="TABLE")
    assert res["PrincipalResourcePermissions"] == [
        table_response(
            principal=principal_1, catalog_id=catalog_id, db=db_1, table=table_1
        ),
    ]

    res = client.list_permissions(CatalogId=catalog_id, ResourceType="CATALOG")
    assert res["PrincipalResourcePermissions"] == [
        catalog_response(principal=principal_1),
    ]


@mock_aws
def test_list_permissions_filtered_for_resource_db():
    client = boto3.client("lakeformation", region_name="eu-west-2")
    catalog_id = "000000000000"
    principal_1 = "principal_1"
    db_1 = "db_1"
    db_2 = "db_2"

    grant_db_permissions(
        client=client, catalog_id=catalog_id, principal=principal_1, db=db_1
    )
    grant_db_permissions(
        client=client, catalog_id=catalog_id, principal=principal_1, db=db_2
    )

    res = client.list_permissions(
        CatalogId=catalog_id, Resource={"Database": {"Name": db_1}}
    )

    assert res["PrincipalResourcePermissions"] == [
        db_response(principal=principal_1, catalog_id=catalog_id, db=db_1),
    ]

    res = client.list_permissions(
        CatalogId=catalog_id, Resource={"Database": {"Name": db_2}}
    )
    assert res["PrincipalResourcePermissions"] == [
        db_response(principal=principal_1, catalog_id=catalog_id, db=db_2),
    ]


@mock_aws
def test_list_permissions_filtered_for_resource_table():
    client = boto3.client("lakeformation", region_name="eu-west-2")
    catalog_id = "000000000000"
    principal_1 = "principal_1"
    db_1 = "db_1"
    table_1 = "table_1"
    table_2 = "table_2"

    grant_table_permissions(
        client=client,
        catalog_id=catalog_id,
        principal=principal_1,
        db=db_1,
        table=table_1,
    )
    grant_table_permissions(
        client=client,
        catalog_id=catalog_id,
        principal=principal_1,
        db=db_1,
        table=table_2,
    )

    res = client.list_permissions(
        CatalogId=catalog_id,
        Resource={"Table": {"DatabaseName": db_1, "Name": table_1}},
    )

    assert res["PrincipalResourcePermissions"] == [
        table_response(
            principal=principal_1, catalog_id=catalog_id, db=db_1, table=table_1
        ),
    ]

    res = client.list_permissions(
        CatalogId=catalog_id,
        Resource={"Table": {"DatabaseName": db_1, "Name": table_2}},
    )

    assert res["PrincipalResourcePermissions"] == [
        table_response(
            principal=principal_1, catalog_id=catalog_id, db=db_1, table=table_2
        ),
    ]


@mock_aws
def test_list_permissions_filtered_for_resource_data_location():
    client = boto3.client("lakeformation", region_name="eu-west-2")
    catalog_id = "000000000000"
    principal = "principal"
    data_location_resource_arn_1 = "resource_arn_1"
    data_location_resource_arn_2 = "resource_arn_2"

    grant_data_location_permissions(
        catalog_id=catalog_id,
        client=client,
        resource_arn=data_location_resource_arn_1,
        principal=principal,
    )
    grant_data_location_permissions(
        catalog_id=catalog_id,
        client=client,
        resource_arn=data_location_resource_arn_2,
        principal=principal,
    )

    res = client.list_permissions(
        CatalogId=catalog_id,
        Resource={"DataLocation": {"ResourceArn": data_location_resource_arn_1}},
    )
    assert res["PrincipalResourcePermissions"] == [
        data_location_response(principal, resource_arn=data_location_resource_arn_1)
    ]

    res = client.list_permissions(
        CatalogId=catalog_id,
        Resource={"DataLocation": {"ResourceArn": data_location_resource_arn_2}},
    )

    assert res["PrincipalResourcePermissions"] == [
        data_location_response(principal, resource_arn=data_location_resource_arn_2)
    ]


@mock_aws
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
    assert resp["PrincipalResourcePermissions"][0]["Principal"] == {
        "DataLakePrincipalIdentifier": "asdf"
    }
    assert resp["PrincipalResourcePermissions"][0]["Resource"] == {
        "Database": {"Name": "db"}
    }
    # compare as sets to be order independent
    assert set(resp["PrincipalResourcePermissions"][0]["Permissions"]) == set(
        ["SELECT", "ALTER"]
    )
    assert set(
        resp["PrincipalResourcePermissions"][0]["PermissionsWithGrantOption"]
    ) == set(
        [
            "SELECT",
            "DROP",
        ]
    )


@mock_aws
def test_revoke_permissions_unknown_catalog_id():
    client = boto3.client("lakeformation", region_name="eu-west-2")

    client.grant_permissions(
        CatalogId="valid_id",
        Principal={"DataLakePrincipalIdentifier": "asdf"},
        Resource={"Database": {"Name": "db"}},
        Permissions=["SELECT"],
    )

    resp = client.revoke_permissions(
        CatalogId="different_id",
        Principal={"DataLakePrincipalIdentifier": "asdf"},
        Resource={"Database": {"Name": "db"}},
        Permissions=["SELECT"],
    )

    del resp["ResponseMetadata"]
    assert resp == {}

    resp = client.list_permissions()
    assert len(["PrincipalResourcePermissions"]) == 1


@mock_aws
def test_list_data_cells_filter():
    client = boto3.client("lakeformation", region_name="eu-west-2")

    resp = client.list_data_cells_filter()
    assert resp["DataCellsFilters"] == []


@mock_aws
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
