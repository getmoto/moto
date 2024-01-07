import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID


@mock_aws
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
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 201

    pipeline = response["Pipeline"]
    assert pipeline["Name"] == "testpipeline"
    assert (
        pipeline["Arn"]
        == f"arn:aws:elastictranscoder:{region}:{ACCOUNT_ID}:pipeline/{pipeline['Id']}"
    )
    assert pipeline["Status"] == "Active"
    assert pipeline["InputBucket"] == "inputtest"
    assert pipeline["OutputBucket"] == "outputtest"
    assert pipeline["Role"] == role
    assert pipeline["Notifications"] == {
        "Progressing": "",
        "Completed": "",
        "Warning": "",
        "Error": "",
    }
    assert pipeline["ContentConfig"]["Bucket"] == "outputtest"
    assert pipeline["ContentConfig"]["Permissions"] == []
    assert pipeline["ThumbnailConfig"]["Bucket"] == "outputtest"
    assert pipeline["ThumbnailConfig"]["Permissions"] == []

    assert response["Warnings"] == []


@mock_aws
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
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 201

    pipeline = response["Pipeline"]
    assert pipeline["Name"] == "testpipeline"
    assert (
        pipeline["Arn"]
        == f"arn:aws:elastictranscoder:{region}:{ACCOUNT_ID}:pipeline/{pipeline['Id']}"
    )
    assert pipeline["Status"] == "Active"
    assert pipeline["InputBucket"] == "inputtest"
    assert pipeline["OutputBucket"] == "outputtest"
    assert pipeline["Role"] == role
    assert pipeline["Notifications"] == {
        "Progressing": "",
        "Completed": "",
        "Warning": "",
        "Error": "",
    }
    assert pipeline["ContentConfig"]["Bucket"] == "outputtest"
    assert pipeline["ContentConfig"]["Permissions"] == []
    assert pipeline["ThumbnailConfig"]["Bucket"] == "outputtest"
    assert pipeline["ThumbnailConfig"]["Permissions"] == []


@mock_aws
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
    assert err["Code"] == "ValidationException"
    assert err["Message"] == "[OutputBucket and ContentConfig are mutually exclusive.]"


@mock_aws
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
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "[ThumbnailConfig:Bucket is not allowed to be null if ContentConfig is specified.]"
    )


@mock_aws
def test_create_pipeline_without_role():
    client = boto3.client("elastictranscoder", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.create_pipeline(Name="testpipeline", InputBucket="inputtest", Role="")
    err = ex.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert err["Message"] == "Role cannot be blank"


@mock_aws
def test_create_pipeline_with_invalid_role():
    client = boto3.client("elastictranscoder", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.create_pipeline(
            Name="testpipeline", InputBucket="inputtest", Role="asdf"
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert err["Message"] == "Role ARN is invalid: asdf"


@mock_aws
def test_create_pipeline_without_output():
    client = boto3.client("elastictranscoder", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.create_pipeline(
            Name="testpipeline",
            InputBucket="inputtest",
            Role=create_role_name("nonexistingrole"),
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "[OutputBucket and ContentConfig:Bucket are not allowed to both be null.]"
    )


@mock_aws
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
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert len(response["Pipelines"]) == 1

    pipeline = response["Pipelines"][0]
    assert pipeline["Name"] == "testpipeline"
    assert (
        pipeline["Arn"]
        == f"arn:aws:elastictranscoder:{region}:{ACCOUNT_ID}:pipeline/{pipeline['Id']}"
    )
    assert pipeline["Status"] == "Active"
    assert pipeline["InputBucket"] == "inputtest"
    assert pipeline["OutputBucket"] == "outputtest"
    assert pipeline["Role"] == role
    assert pipeline["Notifications"] == {
        "Progressing": "",
        "Completed": "",
        "Warning": "",
        "Error": "",
    }
    assert pipeline["ContentConfig"]["Bucket"] == "outputtest"
    assert pipeline["ContentConfig"]["Permissions"] == []
    assert pipeline["ThumbnailConfig"]["Bucket"] == "outputtest"
    assert pipeline["ThumbnailConfig"]["Permissions"] == []


@mock_aws
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

    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    pipeline = response["Pipeline"]
    assert pipeline["Name"] == "testpipeline"
    assert (
        pipeline["Arn"]
        == f"arn:aws:elastictranscoder:{region}:{ACCOUNT_ID}:pipeline/{pipeline['Id']}"
    )
    assert pipeline["Status"] == "Active"
    assert pipeline["InputBucket"] == "inputtest"
    assert pipeline["OutputBucket"] == "outputtest"
    assert pipeline["Role"] == role
    assert pipeline["Notifications"] == {
        "Progressing": "",
        "Completed": "",
        "Warning": "",
        "Error": "",
    }
    assert pipeline["ContentConfig"]["Bucket"] == "outputtest"
    assert pipeline["ContentConfig"]["Permissions"] == []
    assert pipeline["ThumbnailConfig"]["Bucket"] == "outputtest"
    assert pipeline["ThumbnailConfig"]["Permissions"] == []


@mock_aws
def test_read_unknown_pipeline_format():
    region = "us-east-1"
    client = boto3.client("elastictranscoder", region_name=region)

    with pytest.raises(ClientError) as ex:
        client.read_pipeline(Id="unknown-pipeline")
    err = ex.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "1 validation error detected: Value 'unknown-pipeline' at 'id' failed to satisfy constraint: Member must satisfy regular expression pattern: ^\\d{13}-\\w{6}$"
    )


@mock_aws
def test_read_nonexisting_pipeline_format():
    region = "us-east-1"
    client = boto3.client("elastictranscoder", region_name=region)

    pipeline_id = "0000000000000-abcdef"
    with pytest.raises(ClientError) as ex:
        client.read_pipeline(Id=pipeline_id)
    err = ex.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert (
        err["Message"]
        == f"The specified pipeline was not found: account={ACCOUNT_ID}, pipelineId={pipeline_id}."
    )


@mock_aws
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

    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    pipeline = response["Pipeline"]
    assert pipeline["Name"] == "newtestpipeline"
    assert (
        pipeline["Arn"]
        == f"arn:aws:elastictranscoder:{region}:{ACCOUNT_ID}:pipeline/{pipeline['Id']}"
    )
    assert pipeline["Status"] == "Active"
    assert pipeline["InputBucket"] == "inputtest"
    assert pipeline["OutputBucket"] == "outputtest"
    assert pipeline["Role"] == role
    assert pipeline["Notifications"] == {
        "Progressing": "",
        "Completed": "",
        "Warning": "",
        "Error": "",
    }
    assert pipeline["ContentConfig"]["Bucket"] == "outputtest"
    assert pipeline["ContentConfig"]["Permissions"] == []
    assert pipeline["ThumbnailConfig"]["Bucket"] == "outputtest"
    assert pipeline["ThumbnailConfig"]["Permissions"] == []


@mock_aws
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

    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    pipeline = response["Pipeline"]
    assert "Id" in pipeline
    assert pipeline["Name"] == "testpipeline"
    assert pipeline["InputBucket"] == "inputtest2"
    assert pipeline["Role"] == newrole


@mock_aws
def test_update_pipeline_with_invalid_id():
    region = "us-east-1"
    client = boto3.client("elastictranscoder", region_name=region)

    with pytest.raises(ClientError) as ex:
        client.update_pipeline(Id="unknown-pipeline")
    err = ex.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "1 validation error detected: Value 'unknown-pipeline' at 'id' failed to satisfy constraint: Member must satisfy regular expression pattern: ^\\d{13}-\\w{6}$"
    )


@mock_aws
def test_update_nonexisting_pipeline():
    region = "us-east-1"
    client = boto3.client("elastictranscoder", region_name=region)

    pipeline_id = "0000000000000-abcdef"
    with pytest.raises(ClientError) as ex:
        client.read_pipeline(Id=pipeline_id)
    err = ex.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert (
        err["Message"]
        == f"The specified pipeline was not found: account={ACCOUNT_ID}, pipelineId={pipeline_id}."
    )


@mock_aws
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
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert len(response["Pipelines"]) == 0


def create_role_name(name):
    return f"arn:aws:iam::{ACCOUNT_ID}:role/{name}"
