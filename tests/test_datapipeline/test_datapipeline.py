import boto.datapipeline
import sure  # noqa # pylint: disable=unused-import
import boto3

from moto import mock_datapipeline
from moto import mock_datapipeline_deprecated
from moto.datapipeline.utils import remove_capitalization_of_dict_keys


def get_value_from_fields(key, fields):
    for field in fields:
        if field["key"] == key:
            return field["stringValue"]


# Has boto3 equivalent
@mock_datapipeline_deprecated
def test_create_pipeline():
    conn = boto.datapipeline.connect_to_region("us-west-2")

    res = conn.create_pipeline("mypipeline", "some-unique-id")

    pipeline_id = res["pipelineId"]
    pipeline_descriptions = conn.describe_pipelines([pipeline_id])[
        "pipelineDescriptionList"
    ]
    pipeline_descriptions.should.have.length_of(1)

    pipeline_description = pipeline_descriptions[0]
    pipeline_description["name"].should.equal("mypipeline")
    pipeline_description["pipelineId"].should.equal(pipeline_id)
    fields = pipeline_description["fields"]

    get_value_from_fields("@pipelineState", fields).should.equal("PENDING")
    get_value_from_fields("uniqueId", fields).should.equal("some-unique-id")


@mock_datapipeline
def test_create_pipeline_boto3():
    conn = boto3.client("datapipeline", region_name="us-west-2")

    res = conn.create_pipeline(name="mypipeline", uniqueId="some-unique-id")

    pipeline_id = res["pipelineId"]
    pipeline_descriptions = conn.describe_pipelines(pipelineIds=[pipeline_id])[
        "pipelineDescriptionList"
    ]
    pipeline_descriptions.should.have.length_of(1)

    pipeline_description = pipeline_descriptions[0]
    pipeline_description["name"].should.equal("mypipeline")
    pipeline_description["pipelineId"].should.equal(pipeline_id)
    fields = pipeline_description["fields"]

    get_value_from_fields("@pipelineState", fields).should.equal("PENDING")
    get_value_from_fields("uniqueId", fields).should.equal("some-unique-id")


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


# Has boto3 equivalent
@mock_datapipeline_deprecated
def test_creating_pipeline_definition():
    conn = boto.datapipeline.connect_to_region("us-west-2")
    res = conn.create_pipeline("mypipeline", "some-unique-id")
    pipeline_id = res["pipelineId"]

    conn.put_pipeline_definition(PIPELINE_OBJECTS, pipeline_id)

    pipeline_definition = conn.get_pipeline_definition(pipeline_id)
    pipeline_definition["pipelineObjects"].should.have.length_of(3)
    default_object = pipeline_definition["pipelineObjects"][0]
    default_object["name"].should.equal("Default")
    default_object["id"].should.equal("Default")
    default_object["fields"].should.equal(
        [{"key": "workerGroup", "stringValue": "workerGroup"}]
    )


@mock_datapipeline
def test_creating_pipeline_definition_boto3():
    conn = boto3.client("datapipeline", region_name="us-west-2")
    res = conn.create_pipeline(name="mypipeline", uniqueId="some-unique-id")
    pipeline_id = res["pipelineId"]

    conn.put_pipeline_definition(
        pipelineId=pipeline_id, pipelineObjects=PIPELINE_OBJECTS
    )

    pipeline_definition = conn.get_pipeline_definition(pipelineId=pipeline_id)
    pipeline_definition["pipelineObjects"].should.have.length_of(3)
    default_object = pipeline_definition["pipelineObjects"][0]
    default_object["name"].should.equal("Default")
    default_object["id"].should.equal("Default")
    default_object["fields"].should.equal(
        [{"key": "workerGroup", "stringValue": "workerGroup"}]
    )


# Has boto3 equivalent
@mock_datapipeline_deprecated
def test_describing_pipeline_objects():
    conn = boto.datapipeline.connect_to_region("us-west-2")
    res = conn.create_pipeline("mypipeline", "some-unique-id")
    pipeline_id = res["pipelineId"]

    conn.put_pipeline_definition(PIPELINE_OBJECTS, pipeline_id)

    objects = conn.describe_objects(["Schedule", "Default"], pipeline_id)[
        "pipelineObjects"
    ]

    objects.should.have.length_of(2)
    default_object = [x for x in objects if x["id"] == "Default"][0]
    default_object["name"].should.equal("Default")
    default_object["fields"].should.equal(
        [{"key": "workerGroup", "stringValue": "workerGroup"}]
    )


@mock_datapipeline
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

    objects.should.have.length_of(2)
    default_object = [x for x in objects if x["id"] == "Default"][0]
    default_object["name"].should.equal("Default")
    default_object["fields"].should.equal(
        [{"key": "workerGroup", "stringValue": "workerGroup"}]
    )


# Has boto3 equivalent
@mock_datapipeline_deprecated
def test_activate_pipeline():
    conn = boto.datapipeline.connect_to_region("us-west-2")

    res = conn.create_pipeline("mypipeline", "some-unique-id")

    pipeline_id = res["pipelineId"]
    conn.activate_pipeline(pipeline_id)

    pipeline_descriptions = conn.describe_pipelines([pipeline_id])[
        "pipelineDescriptionList"
    ]
    pipeline_descriptions.should.have.length_of(1)
    pipeline_description = pipeline_descriptions[0]
    fields = pipeline_description["fields"]

    get_value_from_fields("@pipelineState", fields).should.equal("SCHEDULED")


@mock_datapipeline
def test_activate_pipeline_boto3():
    conn = boto3.client("datapipeline", region_name="us-west-2")
    res = conn.create_pipeline(name="mypipeline", uniqueId="some-unique-id")

    pipeline_id = res["pipelineId"]
    conn.activate_pipeline(pipelineId=pipeline_id)

    pipeline_descriptions = conn.describe_pipelines(pipelineIds=[pipeline_id])[
        "pipelineDescriptionList"
    ]
    pipeline_descriptions.should.have.length_of(1)
    pipeline_description = pipeline_descriptions[0]
    fields = pipeline_description["fields"]

    get_value_from_fields("@pipelineState", fields).should.equal("SCHEDULED")


# Has boto3 equivalent
@mock_datapipeline_deprecated
def test_delete_pipeline():
    conn = boto.datapipeline.connect_to_region("us-west-2")
    res = conn.create_pipeline("mypipeline", "some-unique-id")
    pipeline_id = res["pipelineId"]

    conn.delete_pipeline(pipeline_id)

    response = conn.list_pipelines()

    response["pipelineIdList"].should.have.length_of(0)


@mock_datapipeline
def test_delete_pipeline_boto3():
    conn = boto3.client("datapipeline", region_name="us-west-2")
    res = conn.create_pipeline(name="mypipeline", uniqueId="some-unique-id")
    pipeline_id = res["pipelineId"]

    conn.delete_pipeline(pipelineId=pipeline_id)

    response = conn.list_pipelines()

    response["pipelineIdList"].should.have.length_of(0)


# Has boto3 equivalent
@mock_datapipeline_deprecated
def test_listing_pipelines():
    conn = boto.datapipeline.connect_to_region("us-west-2")
    res1 = conn.create_pipeline("mypipeline1", "some-unique-id1")
    res2 = conn.create_pipeline("mypipeline2", "some-unique-id2")

    response = conn.list_pipelines()

    response["hasMoreResults"].should.be(False)
    response["marker"].should.be.none
    response["pipelineIdList"].should.have.length_of(2)
    response["pipelineIdList"].should.contain(
        {"id": res1["pipelineId"], "name": "mypipeline1"}
    )
    response["pipelineIdList"].should.contain(
        {"id": res2["pipelineId"], "name": "mypipeline2"}
    )


@mock_datapipeline
def test_listing_pipelines_boto3():
    conn = boto3.client("datapipeline", region_name="us-west-2")
    res1 = conn.create_pipeline(name="mypipeline1", uniqueId="some-unique-id1")
    res2 = conn.create_pipeline(name="mypipeline2", uniqueId="some-unique-id2")

    response = conn.list_pipelines()

    response["hasMoreResults"].should.be(False)
    response.shouldnt.have.key("marker")
    response["pipelineIdList"].should.have.length_of(2)
    response["pipelineIdList"].should.contain(
        {"id": res1["pipelineId"], "name": "mypipeline1"}
    )
    response["pipelineIdList"].should.contain(
        {"id": res2["pipelineId"], "name": "mypipeline2"}
    )


# Has boto3 equivalent
@mock_datapipeline_deprecated
def test_listing_paginated_pipelines():
    conn = boto.datapipeline.connect_to_region("us-west-2")
    for i in range(100):
        conn.create_pipeline("mypipeline%d" % i, "some-unique-id%d" % i)

    response = conn.list_pipelines()

    response["hasMoreResults"].should.be(True)
    response["marker"].should.equal(response["pipelineIdList"][-1]["id"])
    response["pipelineIdList"].should.have.length_of(50)


@mock_datapipeline
def test_listing_paginated_pipelines_boto3():
    conn = boto3.client("datapipeline", region_name="us-west-2")
    for i in range(100):
        conn.create_pipeline(name="mypipeline%d" % i, uniqueId="some-unique-id%d" % i)

    response = conn.list_pipelines()

    response["hasMoreResults"].should.be(True)
    response["marker"].should.equal(response["pipelineIdList"][-1]["id"])
    response["pipelineIdList"].should.have.length_of(50)


# testing a helper function
def test_remove_capitalization_of_dict_keys():
    result = remove_capitalization_of_dict_keys(
        {
            "Id": "IdValue",
            "Fields": [{"Key": "KeyValue", "StringValue": "StringValueValue"}],
        }
    )

    result.should.equal(
        {
            "id": "IdValue",
            "fields": [{"key": "KeyValue", "stringValue": "StringValueValue"}],
        }
    )
