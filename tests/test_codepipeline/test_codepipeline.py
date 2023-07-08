import json
from copy import deepcopy
from datetime import datetime

import boto3
from botocore.exceptions import ClientError
import pytest

from moto import mock_codepipeline, mock_iam


expected_pipeline_details = {
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


@mock_codepipeline
def test_create_pipeline():
    client = boto3.client("codepipeline", region_name="us-east-1")

    response = create_basic_codepipeline(client, "test-pipeline")

    assert response["pipeline"] == expected_pipeline_details
    assert response["tags"] == [{"key": "key", "value": "value"}]


@mock_codepipeline
@mock_iam
def test_create_pipeline_errors():
    client = boto3.client("codepipeline", region_name="us-east-1")
    client_iam = boto3.client("iam", region_name="us-east-1")
    create_basic_codepipeline(client, "test-pipeline")

    with pytest.raises(ClientError) as e:
        create_basic_codepipeline(client, "test-pipeline")
    ex = e.value
    assert ex.operation_name == "CreatePipeline"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "InvalidStructureException"
    assert (
        ex.response["Error"]["Message"]
        == "A pipeline with the name 'test-pipeline' already exists in account '123456789012'"
    )

    with pytest.raises(ClientError) as e:
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
    ex = e.value
    assert ex.operation_name == "CreatePipeline"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "InvalidStructureException"
    assert (
        ex.response["Error"]["Message"]
        == "CodePipeline is not authorized to perform AssumeRole on role arn:aws:iam::123456789012:role/not-existing"
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

    with pytest.raises(ClientError) as e:
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
    ex = e.value
    assert ex.operation_name == "CreatePipeline"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "InvalidStructureException"
    assert (
        ex.response["Error"]["Message"]
        == "CodePipeline is not authorized to perform AssumeRole on role arn:aws:iam::123456789012:role/wrong-role"
    )

    with pytest.raises(ClientError) as e:
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
    ex = e.value
    assert ex.operation_name == "CreatePipeline"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "InvalidStructureException"
    assert (
        ex.response["Error"]["Message"]
        == "Pipeline has only 1 stage(s). There should be a minimum of 2 stages in a pipeline"
    )


@mock_codepipeline
def test_get_pipeline():
    client = boto3.client("codepipeline", region_name="us-east-1")
    create_basic_codepipeline(client, "test-pipeline")

    response = client.get_pipeline(name="test-pipeline")

    assert response["pipeline"] == expected_pipeline_details
    assert (
        response["metadata"]["pipelineArn"]
        == "arn:aws:codepipeline:us-east-1:123456789012:test-pipeline"
    )
    assert isinstance(response["metadata"]["created"], datetime)
    assert isinstance(response["metadata"]["updated"], datetime)


@mock_codepipeline
def test_get_pipeline_errors():
    client = boto3.client("codepipeline", region_name="us-east-1")

    with pytest.raises(ClientError) as e:
        client.get_pipeline(name="not-existing")
    ex = e.value
    assert ex.operation_name == "GetPipeline"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "PipelineNotFoundException"
    assert (
        ex.response["Error"]["Message"]
        == "Account '123456789012' does not have a pipeline with name 'not-existing'"
    )


@mock_codepipeline
def test_update_pipeline():
    client = boto3.client("codepipeline", region_name="us-east-1")
    create_basic_codepipeline(client, "test-pipeline")

    response = client.get_pipeline(name="test-pipeline")
    created_time = response["metadata"]["created"]
    updated_time = response["metadata"]["updated"]

    response = client.update_pipeline(
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
                                "S3Bucket": "different-bucket",
                                "S3ObjectKey": "test-object",
                            },
                            "outputArtifacts": [{"name": "artifact"}],
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

    assert response["pipeline"] == {
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

    metadata = client.get_pipeline(name="test-pipeline")["metadata"]
    assert metadata["created"] == created_time
    assert metadata["updated"] > updated_time


@mock_codepipeline
def test_update_pipeline_errors():
    client = boto3.client("codepipeline", region_name="us-east-1")

    with pytest.raises(ClientError) as e:
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
                                "outputArtifacts": [{"name": "artifact"}],
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
    ex = e.value
    assert ex.operation_name == "UpdatePipeline"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "ResourceNotFoundException"
    assert (
        ex.response["Error"]["Message"]
        == "The account with id '123456789012' does not include a pipeline with the name 'not-existing'"
    )


@mock_codepipeline
def test_list_pipelines():
    client = boto3.client("codepipeline", region_name="us-east-1")
    name_1 = "test-pipeline-1"
    create_basic_codepipeline(client, name_1)
    name_2 = "test-pipeline-2"
    create_basic_codepipeline(client, name_2)

    response = client.list_pipelines()

    assert len(response["pipelines"]) == 2
    assert response["pipelines"][0]["name"] == name_1
    assert response["pipelines"][0]["version"] == 1
    assert isinstance(response["pipelines"][0]["created"], datetime)
    assert isinstance(response["pipelines"][0]["updated"], datetime)
    assert response["pipelines"][1]["name"] == name_2
    assert response["pipelines"][1]["version"] == 1
    assert isinstance(response["pipelines"][1]["created"], datetime)
    assert isinstance(response["pipelines"][1]["updated"], datetime)


@mock_codepipeline
def test_delete_pipeline():
    client = boto3.client("codepipeline", region_name="us-east-1")
    name = "test-pipeline"
    create_basic_codepipeline(client, name)
    assert len(client.list_pipelines()["pipelines"]) == 1

    client.delete_pipeline(name=name)

    assert len(client.list_pipelines()["pipelines"]) == 0

    # deleting a not existing pipeline, should raise no exception
    client.delete_pipeline(name=name)


@mock_codepipeline
def test_list_tags_for_resource():
    client = boto3.client("codepipeline", region_name="us-east-1")
    name = "test-pipeline"
    create_basic_codepipeline(client, name)

    response = client.list_tags_for_resource(
        resourceArn=f"arn:aws:codepipeline:us-east-1:123456789012:{name}"
    )
    assert response["tags"] == [{"key": "key", "value": "value"}]


@mock_codepipeline
def test_list_tags_for_resource_errors():
    client = boto3.client("codepipeline", region_name="us-east-1")

    with pytest.raises(ClientError) as e:
        client.list_tags_for_resource(
            resourceArn="arn:aws:codepipeline:us-east-1:123456789012:not-existing"
        )
    ex = e.value
    assert ex.operation_name == "ListTagsForResource"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "ResourceNotFoundException"
    assert (
        ex.response["Error"]["Message"]
        == "The account with id '123456789012' does not include a pipeline with the name 'not-existing'"
    )


@mock_codepipeline
def test_tag_resource():
    client = boto3.client("codepipeline", region_name="us-east-1")
    name = "test-pipeline"
    create_basic_codepipeline(client, name)

    client.tag_resource(
        resourceArn=f"arn:aws:codepipeline:us-east-1:123456789012:{name}",
        tags=[{"key": "key-2", "value": "value-2"}],
    )

    response = client.list_tags_for_resource(
        resourceArn=f"arn:aws:codepipeline:us-east-1:123456789012:{name}"
    )
    assert response["tags"] == [
        {"key": "key", "value": "value"},
        {"key": "key-2", "value": "value-2"},
    ]


@mock_codepipeline
def test_tag_resource_errors():
    client = boto3.client("codepipeline", region_name="us-east-1")
    name = "test-pipeline"
    create_basic_codepipeline(client, name)

    with pytest.raises(ClientError) as e:
        client.tag_resource(
            resourceArn="arn:aws:codepipeline:us-east-1:123456789012:not-existing",
            tags=[{"key": "key-2", "value": "value-2"}],
        )
    ex = e.value
    assert ex.operation_name == "TagResource"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "ResourceNotFoundException"
    assert (
        ex.response["Error"]["Message"]
        == "The account with id '123456789012' does not include a pipeline with the name 'not-existing'"
    )

    with pytest.raises(ClientError) as e:
        client.tag_resource(
            resourceArn=f"arn:aws:codepipeline:us-east-1:123456789012:{name}",
            tags=[{"key": "aws:key", "value": "value"}],
        )
    ex = e.value
    assert ex.operation_name == "TagResource"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "InvalidTagsException"
    assert (
        ex.response["Error"]["Message"]
        == "Not allowed to modify system tags. System tags start with 'aws:'. msg=[Caller is an end user and not allowed to mutate system tags]"
    )

    with pytest.raises(ClientError) as e:
        client.tag_resource(
            resourceArn=f"arn:aws:codepipeline:us-east-1:123456789012:{name}",
            tags=[{"key": f"key-{i}", "value": f"value-{i}"} for i in range(50)],
        )
    ex = e.value
    assert ex.operation_name == "TagResource"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "TooManyTagsException"
    assert (
        ex.response["Error"]["Message"]
        == f"Tag limit exceeded for resource [arn:aws:codepipeline:us-east-1:123456789012:{name}]."
    )


@mock_codepipeline
def test_untag_resource():
    client = boto3.client("codepipeline", region_name="us-east-1")
    name = "test-pipeline"
    create_basic_codepipeline(client, name)

    response = client.list_tags_for_resource(
        resourceArn=f"arn:aws:codepipeline:us-east-1:123456789012:{name}"
    )
    assert response["tags"] == [{"key": "key", "value": "value"}]

    client.untag_resource(
        resourceArn=f"arn:aws:codepipeline:us-east-1:123456789012:{name}",
        tagKeys=["key"],
    )

    response = client.list_tags_for_resource(
        resourceArn=f"arn:aws:codepipeline:us-east-1:123456789012:{name}"
    )
    assert len(response["tags"]) == 0

    # removing a not existing tag should raise no exception
    client.untag_resource(
        resourceArn=f"arn:aws:codepipeline:us-east-1:123456789012:{name}",
        tagKeys=["key"],
    )


@mock_codepipeline
def test_untag_resource_errors():
    client = boto3.client("codepipeline", region_name="us-east-1")

    with pytest.raises(ClientError) as e:
        client.untag_resource(
            resourceArn="arn:aws:codepipeline:us-east-1:123456789012:not-existing",
            tagKeys=["key"],
        )
    ex = e.value
    assert ex.operation_name == "UntagResource"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "ResourceNotFoundException"
    assert (
        ex.response["Error"]["Message"]
        == "The account with id '123456789012' does not include a pipeline with the name 'not-existing'"
    )


simple_trust_policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {"Service": "codepipeline.amazonaws.com"},
            "Action": "sts:AssumeRole",
        }
    ],
}


@mock_iam
def get_role_arn(name="test-role", trust_policy=None):
    client = boto3.client("iam", region_name="us-east-1")
    try:
        return client.get_role(RoleName=name)["Role"]["Arn"]
    except ClientError:
        if trust_policy is None:
            trust_policy = simple_trust_policy
        return client.create_role(
            RoleName=name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
        )["Role"]["Arn"]


def create_basic_codepipeline(client, name, role_arn=None, tags=None):
    if role_arn is None:
        role_arn = get_role_arn()
    if tags is None:
        tags = [{"key": "key", "value": "value"}]
    return client.create_pipeline(
        pipeline={
            "name": name,
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
                            "outputArtifacts": [{"name": "artifact"}],
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
        tags=tags,
    )


extended_trust_policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {"Service": "codebuild.amazonaws.com"},
            "Action": "sts:AssumeRole",
        },
        {
            "Effect": "Allow",
            "Principal": {"Service": "codepipeline.amazonaws.com"},
            "Action": "sts:AssumeRole",
        },
    ],
}


@mock_codepipeline
def test_create_pipeline_with_extended_trust_policy():
    client = boto3.client("codepipeline", region_name="us-east-1")

    role_arn = get_role_arn(
        name="test-role-extended", trust_policy=extended_trust_policy
    )
    response = create_basic_codepipeline(client, "test-pipeline", role_arn=role_arn)

    extended_pipeline_details = deepcopy(expected_pipeline_details)
    extended_pipeline_details["roleArn"] = role_arn

    assert response["pipeline"] == extended_pipeline_details
    assert response["tags"] == [{"key": "key", "value": "value"}]


@mock_codepipeline
def test_create_pipeline_without_tags():
    client = boto3.client("codepipeline", region_name="us-east-1")

    response = create_basic_codepipeline(client, "test-pipeline", tags=[])

    assert response["pipeline"] == expected_pipeline_details
    assert response["tags"] == []
