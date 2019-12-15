import json

import boto3
import sure  # noqa
from botocore.exceptions import ClientError
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
