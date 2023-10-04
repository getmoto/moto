import boto3

from uuid import uuid4

from . import lakeformation_aws_verified


@lakeformation_aws_verified
def test_add_unknown_lf_tags(
    bucket_name=None,  # pylint: disable=unused-argument
    db_name=None,
    table_name=None,  # pylint: disable=unused-argument
    column_name=None,  # pylint: disable=unused-argument
):
    client = boto3.client("lakeformation", region_name="eu-west-2")
    sts = boto3.client("sts", "eu-west-2")
    account_id = sts.get_caller_identity()["Account"]

    failures = client.add_lf_tags_to_resource(
        Resource={"Database": {"Name": db_name}},
        LFTags=[{"TagKey": "unknown-tag", "TagValues": ["value"]}],
    )["Failures"]
    assert len(failures) == 1
    assert failures[0]["LFTag"] == {
        "CatalogId": account_id,
        "TagKey": "unknown-tag",
        "TagValues": ["value"],
    }
    assert failures[0]["Error"] == {
        "ErrorCode": "EntityNotFoundException",
        "ErrorMessage": "Tag or tag value does not exist.",
    }


@lakeformation_aws_verified
def test_tag_lakeformation_database(
    bucket_name=None,  # pylint: disable=unused-argument
    db_name=None,
    table_name=None,  # pylint: disable=unused-argument
    column_name=None,  # pylint: disable=unused-argument
):
    client = boto3.client("lakeformation", region_name="eu-west-2")
    sts = boto3.client("sts", "eu-west-2")
    account_id = sts.get_caller_identity()["Account"]

    tag_name = str(uuid4())[0:6]
    client.create_lf_tag(TagKey=tag_name, TagValues=["value1"])
    resp = client.add_lf_tags_to_resource(
        Resource={"Database": {"Name": db_name}},
        LFTags=[{"TagKey": tag_name, "TagValues": ["value1"]}],
    )
    assert resp["Failures"] == []

    tags = client.get_resource_lf_tags(Resource={"Database": {"Name": db_name}})[
        "LFTagOnDatabase"
    ]
    assert tags == [
        {"CatalogId": account_id, "TagKey": tag_name, "TagValues": ["value1"]}
    ]

    client.update_lf_tag(TagKey=tag_name, TagValuesToAdd=["value2"])

    all_tags = client.list_lf_tags()["LFTags"]
    our_tag = next(tag for tag in all_tags if tag["TagKey"] == tag_name)
    assert set(our_tag["TagValues"]) == {"value1", "value2"}

    # The value for this particular resource has not been updated
    db_tags = client.get_resource_lf_tags(Resource={"Database": {"Name": db_name}})[
        "LFTagOnDatabase"
    ]
    assert db_tags == [
        {"CatalogId": account_id, "TagKey": tag_name, "TagValues": ["value1"]}
    ]

    # Update the existing tags for this resource
    client.add_lf_tags_to_resource(
        Resource={"Database": {"Name": db_name}},
        LFTags=[{"TagKey": tag_name, "TagValues": ["value2"]}],
    )

    db_tags = client.get_resource_lf_tags(Resource={"Database": {"Name": db_name}})[
        "LFTagOnDatabase"
    ]
    assert db_tags == [
        {"CatalogId": account_id, "TagKey": tag_name, "TagValues": ["value2"]}
    ]

    # Try remove and re-add
    client.remove_lf_tags_from_resource(
        Resource={"Database": {"Name": db_name}},
        LFTags=[{"TagKey": tag_name, "TagValues": ["value2"]}],
    )

    assert "LFTagOnDatabase" not in client.get_resource_lf_tags(
        Resource={"Database": {"Name": db_name}}
    )

    client.add_lf_tags_to_resource(
        Resource={"Database": {"Name": db_name}},
        LFTags=[{"TagKey": tag_name, "TagValues": ["value1"]}],
    )

    db_tags = client.get_resource_lf_tags(Resource={"Database": {"Name": db_name}})[
        "LFTagOnDatabase"
    ]
    assert db_tags == [
        {"CatalogId": account_id, "TagKey": tag_name, "TagValues": ["value1"]}
    ]

    # Deleting the tag automatically deletes it from any resource
    client.delete_lf_tag(TagKey=tag_name)

    assert "LFTagOnDatabase" not in client.get_resource_lf_tags(
        Resource={"Database": {"Name": db_name}}
    )


@lakeformation_aws_verified
def test_tag_lakeformation_table(
    bucket_name=None,  # pylint: disable=unused-argument
    db_name=None,
    table_name=None,
    column_name=None,  # pylint: disable=unused-argument
):
    client = boto3.client("lakeformation", region_name="eu-west-2")
    sts = boto3.client("sts", "eu-west-2")
    account_id = sts.get_caller_identity()["Account"]

    tag_name = str(uuid4())[0:6]
    client.create_lf_tag(TagKey=tag_name, TagValues=["value1"])
    resp = client.add_lf_tags_to_resource(
        Resource={"Table": {"DatabaseName": db_name, "Name": table_name}},
        LFTags=[{"TagKey": tag_name, "TagValues": ["value1"]}],
    )
    assert resp["Failures"] == []

    tags = client.get_resource_lf_tags(
        Resource={"Table": {"DatabaseName": db_name, "Name": table_name}},
    )["LFTagsOnTable"]
    assert tags == [
        {"CatalogId": account_id, "TagKey": tag_name, "TagValues": ["value1"]}
    ]

    client.update_lf_tag(TagKey=tag_name, TagValuesToAdd=["value2"])

    all_tags = client.list_lf_tags()["LFTags"]
    our_tag = next(tag for tag in all_tags if tag["TagKey"] == tag_name)
    assert set(our_tag["TagValues"]) == {"value1", "value2"}

    # The value for this particular resource has not been updated
    db_tags = client.get_resource_lf_tags(
        Resource={"Table": {"DatabaseName": db_name, "Name": table_name}},
    )["LFTagsOnTable"]
    assert db_tags == [
        {"CatalogId": account_id, "TagKey": tag_name, "TagValues": ["value1"]}
    ]

    # Update the existing tags for this resource
    client.add_lf_tags_to_resource(
        Resource={"Table": {"DatabaseName": db_name, "Name": table_name}},
        LFTags=[{"TagKey": tag_name, "TagValues": ["value2"]}],
    )

    db_tags = client.get_resource_lf_tags(
        Resource={"Table": {"DatabaseName": db_name, "Name": table_name}}
    )["LFTagsOnTable"]
    assert db_tags == [
        {"CatalogId": account_id, "TagKey": tag_name, "TagValues": ["value2"]}
    ]

    # Try remove and re-add
    client.remove_lf_tags_from_resource(
        Resource={"Table": {"DatabaseName": db_name, "Name": table_name}},
        LFTags=[{"TagKey": tag_name, "TagValues": ["value2"]}],
    )

    assert "LFTagsOnTable" not in client.get_resource_lf_tags(
        Resource={"Table": {"DatabaseName": db_name, "Name": table_name}}
    )

    client.add_lf_tags_to_resource(
        Resource={"Table": {"DatabaseName": db_name, "Name": table_name}},
        LFTags=[{"TagKey": tag_name, "TagValues": ["value1"]}],
    )

    db_tags = client.get_resource_lf_tags(
        Resource={"Table": {"DatabaseName": db_name, "Name": table_name}}
    )["LFTagsOnTable"]
    assert db_tags == [
        {"CatalogId": account_id, "TagKey": tag_name, "TagValues": ["value1"]}
    ]

    # Deleting the tag automatically deletes it from any resource
    client.delete_lf_tag(TagKey=tag_name)

    assert "LFTagsOnTable" not in client.get_resource_lf_tags(
        Resource={"Table": {"DatabaseName": db_name, "Name": table_name}}
    )


@lakeformation_aws_verified
def test_tag_lakeformation_columns(
    bucket_name=None,  # pylint: disable=unused-argument
    db_name=None,
    table_name=None,
    column_name=None,
):
    client = boto3.client("lakeformation", region_name="eu-west-2")
    sts = boto3.client("sts", "eu-west-2")
    account_id = sts.get_caller_identity()["Account"]

    tag_name = str(uuid4())[0:6]
    client.create_lf_tag(TagKey=tag_name, TagValues=["value1"])
    resp = client.add_lf_tags_to_resource(
        Resource={
            "TableWithColumns": {
                "DatabaseName": db_name,
                "Name": table_name,
                "ColumnNames": [column_name],
            }
        },
        LFTags=[{"TagKey": tag_name, "TagValues": ["value1"]}],
    )
    assert resp["Failures"] == []

    tags = client.get_resource_lf_tags(
        Resource={
            "TableWithColumns": {
                "DatabaseName": db_name,
                "Name": table_name,
                "ColumnNames": [column_name],
            }
        },
    )["LFTagsOnColumns"]
    assert tags == [
        {
            "Name": column_name,
            "LFTags": [
                {"CatalogId": account_id, "TagKey": tag_name, "TagValues": ["value1"]}
            ],
        }
    ]

    client.update_lf_tag(TagKey=tag_name, TagValuesToAdd=["value2"])

    all_tags = client.list_lf_tags()["LFTags"]
    our_tag = next(tag for tag in all_tags if tag["TagKey"] == tag_name)
    assert set(our_tag["TagValues"]) == {"value1", "value2"}

    # The value for this particular resource has not been updated
    tags = client.get_resource_lf_tags(
        Resource={
            "TableWithColumns": {
                "DatabaseName": db_name,
                "Name": table_name,
                "ColumnNames": [column_name],
            }
        },
    )["LFTagsOnColumns"]
    assert tags == [
        {
            "Name": column_name,
            "LFTags": [
                {"CatalogId": account_id, "TagKey": tag_name, "TagValues": ["value1"]}
            ],
        }
    ]

    # Update the existing tags for this resource
    client.add_lf_tags_to_resource(
        Resource={
            "TableWithColumns": {
                "DatabaseName": db_name,
                "Name": table_name,
                "ColumnNames": [column_name],
            }
        },
        LFTags=[{"TagKey": tag_name, "TagValues": ["value2"]}],
    )

    tags = client.get_resource_lf_tags(
        Resource={
            "TableWithColumns": {
                "DatabaseName": db_name,
                "Name": table_name,
                "ColumnNames": [column_name],
            }
        }
    )["LFTagsOnColumns"]
    assert tags == [
        {
            "Name": column_name,
            "LFTags": [
                {"CatalogId": account_id, "TagKey": tag_name, "TagValues": ["value2"]}
            ],
        }
    ]

    # Try remove and re-add
    client.remove_lf_tags_from_resource(
        Resource={
            "TableWithColumns": {
                "DatabaseName": db_name,
                "Name": table_name,
                "ColumnNames": [column_name],
            }
        },
        LFTags=[{"TagKey": tag_name, "TagValues": ["value2"]}],
    )

    assert "LFTagsOnColumns" not in client.get_resource_lf_tags(
        Resource={
            "TableWithColumns": {
                "DatabaseName": db_name,
                "Name": table_name,
                "ColumnNames": [column_name],
            }
        }
    )

    client.add_lf_tags_to_resource(
        Resource={
            "TableWithColumns": {
                "DatabaseName": db_name,
                "Name": table_name,
                "ColumnNames": [column_name],
            }
        },
        LFTags=[{"TagKey": tag_name, "TagValues": ["value1"]}],
    )

    tags = client.get_resource_lf_tags(
        Resource={
            "TableWithColumns": {
                "DatabaseName": db_name,
                "Name": table_name,
                "ColumnNames": [column_name],
            }
        }
    )["LFTagsOnColumns"]
    assert tags == [
        {
            "Name": column_name,
            "LFTags": [
                {"CatalogId": account_id, "TagKey": tag_name, "TagValues": ["value1"]}
            ],
        }
    ]

    # Deleting the tag automatically deletes it from any resource
    client.delete_lf_tag(TagKey=tag_name)

    assert "LFTagsOnColumns" not in client.get_resource_lf_tags(
        Resource={
            "TableWithColumns": {
                "DatabaseName": db_name,
                "Name": table_name,
                "ColumnNames": [column_name],
            }
        }
    )


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
