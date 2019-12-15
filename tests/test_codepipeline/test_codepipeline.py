import json
from datetime import datetime, timezone

import boto3
import sure  # noqa
from botocore.exceptions import ClientError
from freezegun import freeze_time
from nose.tools import assert_raises

from moto import mock_codepipeline, mock_iam


@mock_codepipeline
def test_create_pipeline():
    client = boto3.client("codepipeline", region_name="us-east-1")

    response = client.create_pipeline(
        pipeline={
            "name": "test-pipeline",
            "roleArn": get_role_arn(),
            "artifactStore": {
                "type": "S3",
                "location": "codepipeline-us-east-1-123456789012",
            },
            "stages": [
                {
                    "name": "Stage-1",
                    "actions": [
                        {
                            "name": "Action-1",
                            "actionTypeId": {
                                "category": "Source",
                                "owner": "AWS",
                                "provider": "S3",
                                "version": "1",
                            },
                            "configuration": {
                                "S3Bucket": "test-bucket",
                                "S3ObjectKey": "test-object",
                            },
                            "outputArtifacts": [{"name": "artifact"},],
                        },
                    ],
                },
                {
                    "name": "Stage-2",
                    "actions": [
                        {
                            "name": "Action-1",
                            "actionTypeId": {
                                "category": "Approval",
                                "owner": "AWS",
                                "provider": "Manual",
                                "version": "1",
                            },
                        },
                    ],
                },
            ],
        },
        tags=[{"key": "key", "value": "value"}],
    )

    response["pipeline"].should.equal(
        {
            "name": "test-pipeline",
            "roleArn": "arn:aws:iam::123456789012:role/test-role",
            "artifactStore": {
                "type": "S3",
                "location": "codepipeline-us-east-1-123456789012",
            },
            "stages": [
                {
                    "name": "Stage-1",
                    "actions": [
                        {
                            "name": "Action-1",
                            "actionTypeId": {
                                "category": "Source",
                                "owner": "AWS",
                                "provider": "S3",
                                "version": "1",
                            },
                            "runOrder": 1,
                            "configuration": {
                                "S3Bucket": "test-bucket",
                                "S3ObjectKey": "test-object",
                            },
                            "outputArtifacts": [{"name": "artifact"}],
                            "inputArtifacts": [],
                        }
                    ],
                },
                {
                    "name": "Stage-2",
                    "actions": [
                        {
                            "name": "Action-1",
                            "actionTypeId": {
                                "category": "Approval",
                                "owner": "AWS",
                                "provider": "Manual",
                                "version": "1",
                            },
                            "runOrder": 1,
                            "configuration": {},
                            "outputArtifacts": [],
                            "inputArtifacts": [],
                        }
                    ],
                },
            ],
            "version": 1,
        }
    )
    response["tags"].should.equal([{"key": "key", "value": "value"}])


@mock_codepipeline
@mock_iam
def test_create_pipeline_errors():
    client = boto3.client("codepipeline", region_name="us-east-1")
    client_iam = boto3.client("iam", region_name="us-east-1")
    client.create_pipeline(
        pipeline={
            "name": "test-pipeline",
            "roleArn": get_role_arn(),
            "artifactStore": {
                "type": "S3",
                "location": "codepipeline-us-east-1-123456789012",
            },
            "stages": [
                {
                    "name": "Stage-1",
                    "actions": [
                        {
                            "name": "Action-1",
                            "actionTypeId": {
                                "category": "Source",
                                "owner": "AWS",
                                "provider": "S3",
                                "version": "1",
                            },
                            "configuration": {
                                "S3Bucket": "test-bucket",
                                "S3ObjectKey": "test-object",
                            },
                            "outputArtifacts": [{"name": "artifact"},],
                        },
                    ],
                },
                {
                    "name": "Stage-2",
                    "actions": [
                        {
                            "name": "Action-1",
                            "actionTypeId": {
                                "category": "Approval",
                                "owner": "AWS",
                                "provider": "Manual",
                                "version": "1",
                            },
                        },
                    ],
                },
            ],
        }
    )

    with assert_raises(ClientError) as e:
        client.create_pipeline(
            pipeline={
                "name": "test-pipeline",
                "roleArn": get_role_arn(),
                "artifactStore": {
                    "type": "S3",
                    "location": "codepipeline-us-east-1-123456789012",
                },
                "stages": [
                    {
                        "name": "Stage-1",
                        "actions": [
                            {
                                "name": "Action-1",
                                "actionTypeId": {
                                    "category": "Source",
                                    "owner": "AWS",
                                    "provider": "S3",
                                    "version": "1",
                                },
                                "configuration": {
                                    "S3Bucket": "test-bucket",
                                    "S3ObjectKey": "test-object",
                                },
                                "outputArtifacts": [{"name": "artifact"},],
                            },
                        ],
                    },
                    {
                        "name": "Stage-2",
                        "actions": [
                            {
                                "name": "Action-1",
                                "actionTypeId": {
                                    "category": "Approval",
                                    "owner": "AWS",
                                    "provider": "Manual",
                                    "version": "1",
                                },
                            },
                        ],
                    },
                ],
            }
        )
    ex = e.exception
    ex.operation_name.should.equal("CreatePipeline")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("InvalidStructureException")
    ex.response["Error"]["Message"].should.equal(
        "A pipeline with the name 'test-pipeline' already exists in account '123456789012'"
    )

    with assert_raises(ClientError) as e:
        client.create_pipeline(
            pipeline={
                "name": "invalid-pipeline",
                "roleArn": "arn:aws:iam::123456789012:role/not-existing",
                "artifactStore": {
                    "type": "S3",
                    "location": "codepipeline-us-east-1-123456789012",
                },
                "stages": [
                    {
                        "name": "Stage-1",
                        "actions": [
                            {
                                "name": "Action-1",
                                "actionTypeId": {
                                    "category": "Source",
                                    "owner": "AWS",
                                    "provider": "S3",
                                    "version": "1",
                                },
                                "runOrder": 1,
                            },
                        ],
                    },
                ],
            }
        )
    ex = e.exception
    ex.operation_name.should.equal("CreatePipeline")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("InvalidStructureException")
    ex.response["Error"]["Message"].should.equal(
        "CodePipeline is not authorized to perform AssumeRole on role arn:aws:iam::123456789012:role/not-existing"
    )

    wrong_role_arn = client_iam.create_role(
        RoleName="wrong-role",
        AssumeRolePolicyDocument=json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"Service": "s3.amazonaws.com"},
                        "Action": "sts:AssumeRole",
                    }
                ],
            }
        ),
    )["Role"]["Arn"]

    with assert_raises(ClientError) as e:
        client.create_pipeline(
            pipeline={
                "name": "invalid-pipeline",
                "roleArn": wrong_role_arn,
                "artifactStore": {
                    "type": "S3",
                    "location": "codepipeline-us-east-1-123456789012",
                },
                "stages": [
                    {
                        "name": "Stage-1",
                        "actions": [
                            {
                                "name": "Action-1",
                                "actionTypeId": {
                                    "category": "Source",
                                    "owner": "AWS",
                                    "provider": "S3",
                                    "version": "1",
                                },
                                "runOrder": 1,
                            },
                        ],
                    },
                ],
            }
        )
    ex = e.exception
    ex.operation_name.should.equal("CreatePipeline")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("InvalidStructureException")
    ex.response["Error"]["Message"].should.equal(
        "CodePipeline is not authorized to perform AssumeRole on role arn:aws:iam::123456789012:role/wrong-role"
    )

    with assert_raises(ClientError) as e:
        client.create_pipeline(
            pipeline={
                "name": "invalid-pipeline",
                "roleArn": get_role_arn(),
                "artifactStore": {
                    "type": "S3",
                    "location": "codepipeline-us-east-1-123456789012",
                },
                "stages": [
                    {
                        "name": "Stage-1",
                        "actions": [
                            {
                                "name": "Action-1",
                                "actionTypeId": {
                                    "category": "Source",
                                    "owner": "AWS",
                                    "provider": "S3",
                                    "version": "1",
                                },
                                "runOrder": 1,
                            },
                        ],
                    },
                ],
            }
        )
    ex = e.exception
    ex.operation_name.should.equal("CreatePipeline")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("InvalidStructureException")
    ex.response["Error"]["Message"].should.equal(
        "Pipeline has only 1 stage(s). There should be a minimum of 2 stages in a pipeline"
    )


@freeze_time("2019-01-01 12:00:00")
@mock_codepipeline
def test_get_pipeline():
    client = boto3.client("codepipeline", region_name="us-east-1")
    client.create_pipeline(
        pipeline={
            "name": "test-pipeline",
            "roleArn": get_role_arn(),
            "artifactStore": {
                "type": "S3",
                "location": "codepipeline-us-east-1-123456789012",
            },
            "stages": [
                {
                    "name": "Stage-1",
                    "actions": [
                        {
                            "name": "Action-1",
                            "actionTypeId": {
                                "category": "Source",
                                "owner": "AWS",
                                "provider": "S3",
                                "version": "1",
                            },
                            "configuration": {
                                "S3Bucket": "test-bucket",
                                "S3ObjectKey": "test-object",
                            },
                            "outputArtifacts": [{"name": "artifact"},],
                        },
                    ],
                },
                {
                    "name": "Stage-2",
                    "actions": [
                        {
                            "name": "Action-1",
                            "actionTypeId": {
                                "category": "Approval",
                                "owner": "AWS",
                                "provider": "Manual",
                                "version": "1",
                            },
                        },
                    ],
                },
            ],
        },
        tags=[{"key": "key", "value": "value"}],
    )

    response = client.get_pipeline(name="test-pipeline")

    response["pipeline"].should.equal(
        {
            "name": "test-pipeline",
            "roleArn": "arn:aws:iam::123456789012:role/test-role",
            "artifactStore": {
                "type": "S3",
                "location": "codepipeline-us-east-1-123456789012",
            },
            "stages": [
                {
                    "name": "Stage-1",
                    "actions": [
                        {
                            "name": "Action-1",
                            "actionTypeId": {
                                "category": "Source",
                                "owner": "AWS",
                                "provider": "S3",
                                "version": "1",
                            },
                            "runOrder": 1,
                            "configuration": {
                                "S3Bucket": "test-bucket",
                                "S3ObjectKey": "test-object",
                            },
                            "outputArtifacts": [{"name": "artifact"}],
                            "inputArtifacts": [],
                        }
                    ],
                },
                {
                    "name": "Stage-2",
                    "actions": [
                        {
                            "name": "Action-1",
                            "actionTypeId": {
                                "category": "Approval",
                                "owner": "AWS",
                                "provider": "Manual",
                                "version": "1",
                            },
                            "runOrder": 1,
                            "configuration": {},
                            "outputArtifacts": [],
                            "inputArtifacts": [],
                        }
                    ],
                },
            ],
            "version": 1,
        }
    )
    response["metadata"].should.equal(
        {
            "pipelineArn": "arn:aws:codepipeline:us-east-1:123456789012:test-pipeline",
            "created": datetime.now(timezone.utc),
            "updated": datetime.now(timezone.utc),
        }
    )


@mock_codepipeline
def test_get_pipeline_errors():
    client = boto3.client("codepipeline", region_name="us-east-1")

    with assert_raises(ClientError) as e:
        client.get_pipeline(name="not-existing")
    ex = e.exception
    ex.operation_name.should.equal("GetPipeline")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("PipelineNotFoundException")
    ex.response["Error"]["Message"].should.equal(
        "Account '123456789012' does not have a pipeline with name 'not-existing'"
    )


@mock_codepipeline
def test_update_pipeline():
    client = boto3.client("codepipeline", region_name="us-east-1")
    role_arn = get_role_arn()
    with freeze_time("2019-01-01 12:00:00"):
        created_time = datetime.now(timezone.utc)
        client.create_pipeline(
            pipeline={
                "name": "test-pipeline",
                "roleArn": role_arn,
                "artifactStore": {
                    "type": "S3",
                    "location": "codepipeline-us-east-1-123456789012",
                },
                "stages": [
                    {
                        "name": "Stage-1",
                        "actions": [
                            {
                                "name": "Action-1",
                                "actionTypeId": {
                                    "category": "Source",
                                    "owner": "AWS",
                                    "provider": "S3",
                                    "version": "1",
                                },
                                "configuration": {
                                    "S3Bucket": "test-bucket",
                                    "S3ObjectKey": "test-object",
                                },
                                "outputArtifacts": [{"name": "artifact"},],
                            },
                        ],
                    },
                    {
                        "name": "Stage-2",
                        "actions": [
                            {
                                "name": "Action-1",
                                "actionTypeId": {
                                    "category": "Approval",
                                    "owner": "AWS",
                                    "provider": "Manual",
                                    "version": "1",
                                },
                            },
                        ],
                    },
                ],
            },
            tags=[{"key": "key", "value": "value"}],
        )

    with freeze_time("2019-01-02 12:00:00"):
        updated_time = datetime.now(timezone.utc)
        response = client.update_pipeline(
            pipeline={
                "name": "test-pipeline",
                "roleArn": role_arn,
                "artifactStore": {
                    "type": "S3",
                    "location": "codepipeline-us-east-1-123456789012",
                },
                "stages": [
                    {
                        "name": "Stage-1",
                        "actions": [
                            {
                                "name": "Action-1",
                                "actionTypeId": {
                                    "category": "Source",
                                    "owner": "AWS",
                                    "provider": "S3",
                                    "version": "1",
                                },
                                "configuration": {
                                    "S3Bucket": "different-bucket",
                                    "S3ObjectKey": "test-object",
                                },
                                "outputArtifacts": [{"name": "artifact"},],
                            },
                        ],
                    },
                    {
                        "name": "Stage-2",
                        "actions": [
                            {
                                "name": "Action-1",
                                "actionTypeId": {
                                    "category": "Approval",
                                    "owner": "AWS",
                                    "provider": "Manual",
                                    "version": "1",
                                },
                            },
                        ],
                    },
                ],
            }
        )

    response["pipeline"].should.equal(
        {
            "name": "test-pipeline",
            "roleArn": "arn:aws:iam::123456789012:role/test-role",
            "artifactStore": {
                "type": "S3",
                "location": "codepipeline-us-east-1-123456789012",
            },
            "stages": [
                {
                    "name": "Stage-1",
                    "actions": [
                        {
                            "name": "Action-1",
                            "actionTypeId": {
                                "category": "Source",
                                "owner": "AWS",
                                "provider": "S3",
                                "version": "1",
                            },
                            "runOrder": 1,
                            "configuration": {
                                "S3Bucket": "different-bucket",
                                "S3ObjectKey": "test-object",
                            },
                            "outputArtifacts": [{"name": "artifact"}],
                            "inputArtifacts": [],
                        }
                    ],
                },
                {
                    "name": "Stage-2",
                    "actions": [
                        {
                            "name": "Action-1",
                            "actionTypeId": {
                                "category": "Approval",
                                "owner": "AWS",
                                "provider": "Manual",
                                "version": "1",
                            },
                            "runOrder": 1,
                            "configuration": {},
                            "outputArtifacts": [],
                            "inputArtifacts": [],
                        }
                    ],
                },
            ],
            "version": 2,
        }
    )

    response = client.get_pipeline(name="test-pipeline")
    response["metadata"].should.equal(
        {
            "pipelineArn": "arn:aws:codepipeline:us-east-1:123456789012:test-pipeline",
            "created": created_time,
            "updated": updated_time,
        }
    )


@mock_codepipeline
def test_update_pipeline_errors():
    client = boto3.client("codepipeline", region_name="us-east-1")

    with assert_raises(ClientError) as e:
        client.update_pipeline(
            pipeline={
                "name": "not-existing",
                "roleArn": get_role_arn(),
                "artifactStore": {
                    "type": "S3",
                    "location": "codepipeline-us-east-1-123456789012",
                },
                "stages": [
                    {
                        "name": "Stage-1",
                        "actions": [
                            {
                                "name": "Action-1",
                                "actionTypeId": {
                                    "category": "Source",
                                    "owner": "AWS",
                                    "provider": "S3",
                                    "version": "1",
                                },
                                "configuration": {
                                    "S3Bucket": "test-bucket",
                                    "S3ObjectKey": "test-object",
                                },
                                "outputArtifacts": [{"name": "artifact"},],
                            },
                        ],
                    },
                    {
                        "name": "Stage-2",
                        "actions": [
                            {
                                "name": "Action-1",
                                "actionTypeId": {
                                    "category": "Approval",
                                    "owner": "AWS",
                                    "provider": "Manual",
                                    "version": "1",
                                },
                            },
                        ],
                    },
                ],
            }
        )
    ex = e.exception
    ex.operation_name.should.equal("UpdatePipeline")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("ResourceNotFoundException")
    ex.response["Error"]["Message"].should.equal(
        "The account with id '123456789012' does not include a pipeline with the name 'not-existing'"
    )


@mock_iam
def get_role_arn():
    iam = boto3.client("iam", region_name="us-east-1")
    return iam.create_role(
        RoleName="test-role",
        AssumeRolePolicyDocument=json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"Service": "codepipeline.amazonaws.com"},
                        "Action": "sts:AssumeRole",
                    }
                ],
            }
        ),
    )["Role"]["Arn"]
