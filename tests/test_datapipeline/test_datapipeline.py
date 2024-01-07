import boto3

from moto import mock_aws
from moto.datapipeline.utils import remove_capitalization_of_dict_keys


def get_value_from_fields(key, fields):
    for field in fields:
        if field["key"] == key:
            return field["stringValue"]


@mock_aws
def test_create_pipeline_boto3():
    conn = boto3.client("datapipeline", region_name="us-west-2")

    res = conn.create_pipeline(name="mypipeline", uniqueId="some-unique-id")

    pipeline_id = res["pipelineId"]
    pipeline_descriptions = conn.describe_pipelines(pipelineIds=[pipeline_id])[
        "pipelineDescriptionList"
    ]
    assert len(pipeline_descriptions) == 1

    pipeline_description = pipeline_descriptions[0]
    assert pipeline_description["name"] == "mypipeline"
    assert pipeline_description["pipelineId"] == pipeline_id
    fields = pipeline_description["fields"]

    assert get_value_from_fields("@pipelineState", fields) == "PENDING"
    assert get_value_from_fields("uniqueId", fields) == "some-unique-id"


PIPELINE_OBJECTS = [
    {
        "id": "Default",
        "name": "Default",
        "fields": [{"key": "workerGroup", "stringValue": "workerGroup"}],
    },
    {
        "id": "Schedule",
        "name": "Schedule",
        "fields": [
            {"key": "startDateTime", "stringValue": "2012-12-12T00:00:00"},
            {"key": "type", "stringValue": "Schedule"},
            {"key": "period", "stringValue": "1 hour"},
            {"key": "endDateTime", "stringValue": "2012-12-21T18:00:00"},
        ],
    },
    {
        "id": "SayHello",
        "name": "SayHello",
        "fields": [
            {"key": "type", "stringValue": "ShellCommandActivity"},
            {"key": "command", "stringValue": "echo hello"},
            {"key": "parent", "refValue": "Default"},
            {"key": "schedule", "refValue": "Schedule"},
        ],
    },
]


@mock_aws
def test_creating_pipeline_definition_boto3():
    conn = boto3.client("datapipeline", region_name="us-west-2")
    res = conn.create_pipeline(name="mypipeline", uniqueId="some-unique-id")
    pipeline_id = res["pipelineId"]

    conn.put_pipeline_definition(
        pipelineId=pipeline_id, pipelineObjects=PIPELINE_OBJECTS
    )

    pipeline_definition = conn.get_pipeline_definition(pipelineId=pipeline_id)
    assert len(pipeline_definition["pipelineObjects"]) == 3
    default_object = pipeline_definition["pipelineObjects"][0]
    assert default_object["name"] == "Default"
    assert default_object["id"] == "Default"
    assert default_object["fields"] == [
        {"key": "workerGroup", "stringValue": "workerGroup"}
    ]


@mock_aws
def test_describing_pipeline_objects_boto3():
    conn = boto3.client("datapipeline", region_name="us-west-2")
    res = conn.create_pipeline(name="mypipeline", uniqueId="some-unique-id")
    pipeline_id = res["pipelineId"]

    conn.put_pipeline_definition(
        pipelineId=pipeline_id, pipelineObjects=PIPELINE_OBJECTS
    )

    objects = conn.describe_objects(
        pipelineId=pipeline_id, objectIds=["Schedule", "Default"]
    )["pipelineObjects"]

    assert len(objects) == 2
    default_object = [x for x in objects if x["id"] == "Default"][0]
    assert default_object["name"] == "Default"
    assert default_object["fields"] == [
        {"key": "workerGroup", "stringValue": "workerGroup"}
    ]


@mock_aws
def test_activate_pipeline_boto3():
    conn = boto3.client("datapipeline", region_name="us-west-2")
    res = conn.create_pipeline(name="mypipeline", uniqueId="some-unique-id")

    pipeline_id = res["pipelineId"]
    conn.activate_pipeline(pipelineId=pipeline_id)

    pipeline_descriptions = conn.describe_pipelines(pipelineIds=[pipeline_id])[
        "pipelineDescriptionList"
    ]
    assert len(pipeline_descriptions) == 1
    pipeline_description = pipeline_descriptions[0]
    fields = pipeline_description["fields"]

    assert get_value_from_fields("@pipelineState", fields) == "SCHEDULED"


@mock_aws
def test_delete_pipeline_boto3():
    conn = boto3.client("datapipeline", region_name="us-west-2")
    res = conn.create_pipeline(name="mypipeline", uniqueId="some-unique-id")
    pipeline_id = res["pipelineId"]

    conn.delete_pipeline(pipelineId=pipeline_id)

    response = conn.list_pipelines()

    assert len(response["pipelineIdList"]) == 0


@mock_aws
def test_listing_pipelines_boto3():
    conn = boto3.client("datapipeline", region_name="us-west-2")
    res1 = conn.create_pipeline(name="mypipeline1", uniqueId="some-unique-id1")
    res2 = conn.create_pipeline(name="mypipeline2", uniqueId="some-unique-id2")

    response = conn.list_pipelines()

    assert response["hasMoreResults"] is False
    assert "marker" not in response
    objects = response["pipelineIdList"]
    assert len(objects) == 2
    assert {"id": res1["pipelineId"], "name": "mypipeline1"} in objects
    assert {"id": res2["pipelineId"], "name": "mypipeline2"} in objects


@mock_aws
def test_listing_paginated_pipelines_boto3():
    conn = boto3.client("datapipeline", region_name="us-west-2")
    for i in range(100):
        conn.create_pipeline(name=f"mypipeline{i}", uniqueId=f"some-unique-id{i}")

    response = conn.list_pipelines()

    assert response["hasMoreResults"] is True
    assert response["marker"] == response["pipelineIdList"][-1]["id"]
    assert len(response["pipelineIdList"]) == 50


# testing a helper function
def test_remove_capitalization_of_dict_keys():
    result = remove_capitalization_of_dict_keys(
        {
            "Id": "IdValue",
            "Fields": [{"Key": "KeyValue", "StringValue": "StringValueValue"}],
        }
    )

    assert result == {
        "id": "IdValue",
        "fields": [{"key": "KeyValue", "stringValue": "StringValueValue"}],
    }
