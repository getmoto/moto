from __future__ import unicode_literals

from botocore.exceptions import ClientError
import boto3
import sure  # noqa
import pytest
from moto import mock_elastictranscoder
from moto.core import ACCOUNT_ID


@mock_elastictranscoder
def test_create_simple_pipeline():
    region = "us-east-1"
    client = boto3.client("elastictranscoder", region_name=region)

    role = create_role_name("nonexistingrole")
    response = client.create_pipeline(
        Name="testpipeline",
        InputBucket="inputtest",
        OutputBucket="outputtest",
        Role=role,
    )
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(201)

    pipeline = response["Pipeline"]
    pipeline.should.have.key("Id")
    pipeline.should.have.key("Name").being.equal("testpipeline")
    pipeline.should.have.key("Arn").being.equal(
        "arn:aws:elastictranscoder:{}:{}:pipeline/{}".format(
            region, ACCOUNT_ID, pipeline["Id"]
        )
    )
    pipeline.should.have.key("Status").being.equal("Active")
    pipeline.should.have.key("InputBucket").being.equal("inputtest")
    pipeline.should.have.key("OutputBucket").being.equal("outputtest")
    pipeline.should.have.key("Role").being.equal(role)
    pipeline.should.have.key("Notifications").being.equal(
        {"Progressing": "", "Completed": "", "Warning": "", "Error": ""}
    )
    pipeline.should.have.key("ContentConfig")
    pipeline["ContentConfig"].should.have.key("Bucket").being.equal("outputtest")
    pipeline["ContentConfig"].should.have.key("Permissions").being.equal([])
    pipeline.should.have.key("ThumbnailConfig")
    pipeline["ThumbnailConfig"].should.have.key("Bucket").being.equal("outputtest")
    pipeline["ThumbnailConfig"].should.have.key("Permissions").being.equal([])

    response.should.have.key("Warnings").being.equal([])


@mock_elastictranscoder
def test_create_pipeline_with_content_config():
    region = "us-east-1"
    client = boto3.client("elastictranscoder", region_name=region)

    role = create_role_name("nonexistingrole")
    response = client.create_pipeline(
        Name="testpipeline",
        InputBucket="inputtest",
        ContentConfig={"Bucket": "outputtest"},
        ThumbnailConfig={"Bucket": "outputtest"},
        Role=role,
    )
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(201)

    pipeline = response["Pipeline"]
    pipeline.should.have.key("Id")
    pipeline.should.have.key("Name").being.equal("testpipeline")
    pipeline.should.have.key("Arn").being.equal(
        "arn:aws:elastictranscoder:{}:{}:pipeline/{}".format(
            region, ACCOUNT_ID, pipeline["Id"]
        )
    )
    pipeline.should.have.key("Status").being.equal("Active")
    pipeline.should.have.key("InputBucket").being.equal("inputtest")
    pipeline.should.have.key("OutputBucket").being.equal("outputtest")
    pipeline.should.have.key("Role").being.equal(role)
    pipeline.should.have.key("Notifications").being.equal(
        {"Progressing": "", "Completed": "", "Warning": "", "Error": ""}
    )
    pipeline.should.have.key("ContentConfig")
    pipeline["ContentConfig"].should.have.key("Bucket").being.equal("outputtest")
    pipeline["ContentConfig"].should.have.key("Permissions").being.equal([])
    pipeline.should.have.key("ThumbnailConfig")
    pipeline["ThumbnailConfig"].should.have.key("Bucket").being.equal("outputtest")
    pipeline["ThumbnailConfig"].should.have.key("Permissions").being.equal([])


@mock_elastictranscoder
def test_create_pipeline_with_outputbucket_and_content_config():
    region = "us-east-1"
    client = boto3.client("elastictranscoder", region_name=region)

    role = create_role_name("nonexistingrole")
    with pytest.raises(ClientError) as ex:
        client.create_pipeline(
            Name="testpipeline",
            InputBucket="inputtest",
            OutputBucket="outputtest",
            ContentConfig={"Bucket": "configoutputtest"},
            Role=role,
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.equal(
        "[OutputBucket and ContentConfig are mutually exclusive.]"
    )


@mock_elastictranscoder
def test_create_pipeline_without_thumbnail_config():
    region = "us-east-1"
    client = boto3.client("elastictranscoder", region_name=region)

    role = create_role_name("nonexistingrole")
    with pytest.raises(ClientError) as ex:
        client.create_pipeline(
            Name="testpipeline",
            InputBucket="inputtest",
            ContentConfig={"Bucket": "outputtest"},
            Role=role,
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.equal(
        "[ThumbnailConfig:Bucket is not allowed to be null if ContentConfig is specified.]"
    )


@mock_elastictranscoder
def test_create_pipeline_without_role():
    client = boto3.client("elastictranscoder", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.create_pipeline(Name="testpipeline", InputBucket="inputtest", Role="")
    err = ex.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.equal("Role cannot be blank")


@mock_elastictranscoder
def test_create_pipeline_with_invalid_role():
    client = boto3.client("elastictranscoder", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.create_pipeline(
            Name="testpipeline", InputBucket="inputtest", Role="asdf"
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.equal("Role ARN is invalid: asdf")


@mock_elastictranscoder
def test_create_pipeline_without_output():
    client = boto3.client("elastictranscoder", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.create_pipeline(
            Name="testpipeline",
            InputBucket="inputtest",
            Role=create_role_name("nonexistingrole"),
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.equal(
        "[OutputBucket and ContentConfig:Bucket are not allowed to both be null.]"
    )


@mock_elastictranscoder
def test_list_pipelines():
    region = "us-east-1"
    client = boto3.client("elastictranscoder", region_name=region)

    role = create_role_name("nonexistingrole")
    client.create_pipeline(
        Name="testpipeline",
        InputBucket="inputtest",
        OutputBucket="outputtest",
        Role=role,
    )

    response = client.list_pipelines()
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    response.should.have.key("Pipelines").being.length_of(1)

    pipeline = response["Pipelines"][0]
    pipeline.should.have.key("Id")
    pipeline.should.have.key("Name").being.equal("testpipeline")
    pipeline.should.have.key("Arn").being.equal(
        "arn:aws:elastictranscoder:{}:{}:pipeline/{}".format(
            region, ACCOUNT_ID, pipeline["Id"]
        )
    )
    pipeline.should.have.key("Status").being.equal("Active")
    pipeline.should.have.key("InputBucket").being.equal("inputtest")
    pipeline.should.have.key("OutputBucket").being.equal("outputtest")
    pipeline.should.have.key("Role").being.equal(role)
    pipeline.should.have.key("Notifications").being.equal(
        {"Progressing": "", "Completed": "", "Warning": "", "Error": ""}
    )
    pipeline.should.have.key("ContentConfig")
    pipeline["ContentConfig"].should.have.key("Bucket").being.equal("outputtest")
    pipeline["ContentConfig"].should.have.key("Permissions").being.equal([])
    pipeline.should.have.key("ThumbnailConfig")
    pipeline["ThumbnailConfig"].should.have.key("Bucket").being.equal("outputtest")
    pipeline["ThumbnailConfig"].should.have.key("Permissions").being.equal([])


@mock_elastictranscoder
def test_read_pipeline():
    region = "us-east-1"
    client = boto3.client("elastictranscoder", region_name=region)

    role = create_role_name("nonexistingrole")
    pipeline = client.create_pipeline(
        Name="testpipeline",
        InputBucket="inputtest",
        OutputBucket="outputtest",
        Role=role,
    )["Pipeline"]

    response = client.read_pipeline(Id=pipeline["Id"])

    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    response.should.have.key("Pipeline")

    pipeline = response["Pipeline"]
    pipeline.should.have.key("Id")
    pipeline.should.have.key("Name").being.equal("testpipeline")
    pipeline.should.have.key("Arn").being.equal(
        "arn:aws:elastictranscoder:{}:{}:pipeline/{}".format(
            region, ACCOUNT_ID, pipeline["Id"]
        )
    )
    pipeline.should.have.key("Status").being.equal("Active")
    pipeline.should.have.key("InputBucket").being.equal("inputtest")
    pipeline.should.have.key("OutputBucket").being.equal("outputtest")
    pipeline.should.have.key("Role").being.equal(role)
    pipeline.should.have.key("Notifications").being.equal(
        {"Progressing": "", "Completed": "", "Warning": "", "Error": ""}
    )
    pipeline.should.have.key("ContentConfig")
    pipeline["ContentConfig"].should.have.key("Bucket").being.equal("outputtest")
    pipeline["ContentConfig"].should.have.key("Permissions").being.equal([])
    pipeline.should.have.key("ThumbnailConfig")
    pipeline["ThumbnailConfig"].should.have.key("Bucket").being.equal("outputtest")
    pipeline["ThumbnailConfig"].should.have.key("Permissions").being.equal([])


@mock_elastictranscoder
def test_read_unknown_pipeline_format():
    region = "us-east-1"
    client = boto3.client("elastictranscoder", region_name=region)

    with pytest.raises(ClientError) as ex:
        client.read_pipeline(Id="unknown-pipeline")
    err = ex.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.equal(
        "1 validation error detected: Value 'unknown-pipeline' at 'id' failed to satisfy constraint: Member must satisfy regular expression pattern: ^\\d{13}-\\w{6}$"
    )


@mock_elastictranscoder
def test_read_nonexisting_pipeline_format():
    region = "us-east-1"
    client = boto3.client("elastictranscoder", region_name=region)

    pipeline_id = "0000000000000-abcdef"
    with pytest.raises(ClientError) as ex:
        client.read_pipeline(Id=pipeline_id)
    err = ex.value.response["Error"]
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.equal(
        "The specified pipeline was not found: account={}, pipelineId={}.".format(
            ACCOUNT_ID, pipeline_id
        )
    )


@mock_elastictranscoder
def test_update_pipeline_name():
    region = "us-east-1"
    client = boto3.client("elastictranscoder", region_name=region)

    role = create_role_name("nonexistingrole")
    pipeline = client.create_pipeline(
        Name="testpipeline",
        InputBucket="inputtest",
        OutputBucket="outputtest",
        Role=role,
    )["Pipeline"]
    response = client.update_pipeline(Id=pipeline["Id"], Name="newtestpipeline")

    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    response.should.have.key("Pipeline")

    pipeline = response["Pipeline"]
    pipeline.should.have.key("Id")
    pipeline.should.have.key("Name").being.equal("newtestpipeline")
    pipeline.should.have.key("Arn").being.equal(
        "arn:aws:elastictranscoder:{}:{}:pipeline/{}".format(
            region, ACCOUNT_ID, pipeline["Id"]
        )
    )
    pipeline.should.have.key("Status").being.equal("Active")
    pipeline.should.have.key("InputBucket").being.equal("inputtest")
    pipeline.should.have.key("OutputBucket").being.equal("outputtest")
    pipeline.should.have.key("Role").being.equal(role)
    pipeline.should.have.key("Notifications").being.equal(
        {"Progressing": "", "Completed": "", "Warning": "", "Error": ""}
    )
    pipeline.should.have.key("ContentConfig")
    pipeline["ContentConfig"].should.have.key("Bucket").being.equal("outputtest")
    pipeline["ContentConfig"].should.have.key("Permissions").being.equal([])
    pipeline.should.have.key("ThumbnailConfig")
    pipeline["ThumbnailConfig"].should.have.key("Bucket").being.equal("outputtest")
    pipeline["ThumbnailConfig"].should.have.key("Permissions").being.equal([])


@mock_elastictranscoder
def test_update_pipeline_input_and_role():
    region = "us-east-1"
    client = boto3.client("elastictranscoder", region_name=region)

    role = create_role_name("nonexistingrole")
    newrole = create_role_name("newrole")
    pipeline = client.create_pipeline(
        Name="testpipeline",
        InputBucket="inputtest",
        OutputBucket="outputtest",
        Role=role,
    )["Pipeline"]
    response = client.update_pipeline(
        Id=pipeline["Id"], InputBucket="inputtest2", Role=newrole
    )

    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    response.should.have.key("Pipeline")

    pipeline = response["Pipeline"]
    pipeline.should.have.key("Id")
    pipeline.should.have.key("Name").being.equal("testpipeline")
    pipeline.should.have.key("InputBucket").being.equal("inputtest2")
    pipeline.should.have.key("Role").being.equal(newrole)


@mock_elastictranscoder
def test_update_pipeline_with_invalid_id():
    region = "us-east-1"
    client = boto3.client("elastictranscoder", region_name=region)

    with pytest.raises(ClientError) as ex:
        client.update_pipeline(Id="unknown-pipeline")
    err = ex.value.response["Error"]
    err["Code"].should.equal("ValidationException")
    err["Message"].should.equal(
        "1 validation error detected: Value 'unknown-pipeline' at 'id' failed to satisfy constraint: Member must satisfy regular expression pattern: ^\\d{13}-\\w{6}$"
    )


@mock_elastictranscoder
def test_update_nonexisting_pipeline():
    region = "us-east-1"
    client = boto3.client("elastictranscoder", region_name=region)

    pipeline_id = "0000000000000-abcdef"
    with pytest.raises(ClientError) as ex:
        client.read_pipeline(Id=pipeline_id)
    err = ex.value.response["Error"]
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.equal(
        "The specified pipeline was not found: account={}, pipelineId={}.".format(
            ACCOUNT_ID, pipeline_id
        )
    )


@mock_elastictranscoder
def test_delete_pipeline():
    region = "us-east-1"
    client = boto3.client("elastictranscoder", region_name=region)

    role = create_role_name("nonexistingrole")
    pipeline = client.create_pipeline(
        Name="testpipeline",
        InputBucket="inputtest",
        OutputBucket="outputtest",
        Role=role,
    )["Pipeline"]
    client.delete_pipeline(Id=pipeline["Id"])

    response = client.list_pipelines()
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    response.should.have.key("Pipelines").being.length_of(0)


def create_role_name(name):
    return "arn:aws:iam::{}:role/{}".format(ACCOUNT_ID, name)
