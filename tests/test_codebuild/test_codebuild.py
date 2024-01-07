from uuid import uuid1

import boto3
import pytest
from botocore.exceptions import ClientError, ParamValidationError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID


@mock_aws
def test_codebuild_create_project_s3_artifacts():
    client = boto3.client("codebuild", region_name="eu-central-1")

    name = "some_project"
    source = dict()
    source["type"] = "S3"
    # repository location for S3
    source["location"] = "bucketname/path/file.zip"
    # output artifacts
    artifacts = dict()
    artifacts["type"] = "S3"
    artifacts["location"] = "bucketname"

    environment = dict()
    environment["type"] = "LINUX_CONTAINER"
    environment["image"] = "contents_not_validated"
    environment["computeType"] = "BUILD_GENERAL1_SMALL"

    service_role = (
        f"arn:aws:iam::{ACCOUNT_ID}:role/service-role/my-codebuild-service-role"
    )

    project = client.create_project(
        name=name,
        source=source,
        artifacts=artifacts,
        environment=environment,
        serviceRole=service_role,
    )["project"]

    assert "serviceRole" in project
    assert project["name"] == name

    assert project["environment"] == {
        "computeType": "BUILD_GENERAL1_SMALL",
        "image": "contents_not_validated",
        "type": "LINUX_CONTAINER",
    }

    assert project["source"] == {"location": "bucketname/path/file.zip", "type": "S3"}
    assert project["artifacts"] == {"location": "bucketname", "type": "S3"}


@mock_aws
def test_codebuild_create_project_no_artifacts():
    client = boto3.client("codebuild", region_name="eu-central-1")

    name = "some_project"
    source = dict()
    source["type"] = "S3"
    # repository location for S3
    source["location"] = "bucketname/path/file.zip"
    # output artifacts
    artifacts = {"type": "NO_ARTIFACTS"}

    environment = dict()
    environment["type"] = "LINUX_CONTAINER"
    environment["image"] = "contents_not_validated"
    environment["computeType"] = "BUILD_GENERAL1_SMALL"
    service_role = (
        f"arn:aws:iam::{ACCOUNT_ID}:role/service-role/my-codebuild-service-role"
    )

    project = client.create_project(
        name=name,
        source=source,
        artifacts=artifacts,
        environment=environment,
        serviceRole=service_role,
    )["project"]

    assert "serviceRole" in project
    assert project["name"] == name

    assert project["environment"] == {
        "computeType": "BUILD_GENERAL1_SMALL",
        "image": "contents_not_validated",
        "type": "LINUX_CONTAINER",
    }

    assert project["source"] == {"location": "bucketname/path/file.zip", "type": "S3"}

    assert project["artifacts"] == {"type": "NO_ARTIFACTS"}


@mock_aws
def test_codebuild_create_project_with_invalid_inputs():
    client = boto3.client("codebuild", region_name="eu-central-1")

    _input = {
        "source": {"type": "S3", "location": "bucketname/path/file.zip"},
        "artifacts": {"type": "NO_ARTIFACTS"},
        "environment": {
            "type": "LINUX_CONTAINER",
            "image": "contents_not_validated",
            "computeType": "BUILD_GENERAL1_SMALL",
        },
        "serviceRole": f"arn:aws:iam::{ACCOUNT_ID}:role/service-role/my-role",
    }

    # Name too long
    with pytest.raises(client.exceptions.from_code("InvalidInputException")) as err:
        client.create_project(name=("some_project_" * 12), **_input)
    assert err.value.response["Error"]["Code"] == "InvalidInputException"

    # Name invalid
    with pytest.raises(client.exceptions.from_code("InvalidInputException")) as err:
        client.create_project(name="!some_project_", **_input)
    assert err.value.response["Error"]["Code"] == "InvalidInputException"

    # ServiceRole invalid
    _input["serviceRole"] = "arn:aws:iam::0000:role/service-role/my-role"
    with pytest.raises(client.exceptions.from_code("InvalidInputException")) as err:
        client.create_project(name="valid_name", **_input)
    assert err.value.response["Error"]["Code"] == "InvalidInputException"


@mock_aws
def test_codebuild_create_project_when_exists():
    client = boto3.client("codebuild", region_name="eu-central-1")

    name = "some_project"
    source = dict()
    source["type"] = "S3"
    # repository location for S3
    source["location"] = "bucketname/path/file.zip"
    artifacts = {"type": "NO_ARTIFACTS"}

    environment = dict()
    environment["type"] = "LINUX_CONTAINER"
    environment["image"] = "contents_not_validated"
    environment["computeType"] = "BUILD_GENERAL1_SMALL"
    service_role = (
        f"arn:aws:iam::{ACCOUNT_ID}:role/service-role/my-codebuild-service-role"
    )

    client.create_project(
        name=name,
        source=source,
        artifacts=artifacts,
        environment=environment,
        serviceRole=service_role,
    )

    with pytest.raises(ClientError) as err:
        client.create_project(
            name=name,
            source=source,
            artifacts=artifacts,
            environment=environment,
            serviceRole=service_role,
        )
    assert err.value.response["Error"]["Code"] == "ResourceAlreadyExistsException"


@mock_aws
def test_codebuild_list_projects():
    client = boto3.client("codebuild", region_name="eu-central-1")

    source = dict()
    source["type"] = "S3"
    # repository location for S3
    source["location"] = "bucketname/path/file.zip"
    # output artifacts
    artifacts = dict()
    artifacts["type"] = "S3"
    artifacts["location"] = "bucketname"

    environment = dict()
    environment["type"] = "LINUX_CONTAINER"
    environment["image"] = "contents_not_validated"
    environment["computeType"] = "BUILD_GENERAL1_SMALL"
    service_role = (
        f"arn:aws:iam::{ACCOUNT_ID}:role/service-role/my-codebuild-service-role"
    )

    client.create_project(
        name="project1",
        source=source,
        artifacts=artifacts,
        environment=environment,
        serviceRole=service_role,
    )
    client.create_project(
        name="project2",
        source=source,
        artifacts=artifacts,
        environment=environment,
        serviceRole=service_role,
    )

    projects = client.list_projects()

    assert projects["projects"] == ["project1", "project2"]


@mock_aws
def test_codebuild_list_builds_for_project_no_history():
    client = boto3.client("codebuild", region_name="eu-central-1")

    name = "some_project"
    source = dict()
    source["type"] = "S3"
    # repository location for S3
    source["location"] = "bucketname/path/file.zip"
    artifacts = {"type": "NO_ARTIFACTS"}

    environment = dict()
    environment["type"] = "LINUX_CONTAINER"
    environment["image"] = "contents_not_validated"
    environment["computeType"] = "BUILD_GENERAL1_SMALL"
    service_role = (
        f"arn:aws:iam::{ACCOUNT_ID}:role/service-role/my-codebuild-service-role"
    )

    client.create_project(
        name=name,
        source=source,
        artifacts=artifacts,
        environment=environment,
        serviceRole=service_role,
    )
    history = client.list_builds_for_project(projectName=name)

    # no build history if it's never started
    assert history["ids"] == []


@mock_aws
def test_codebuild_list_builds_for_project_with_history():
    client = boto3.client("codebuild", region_name="eu-central-1")

    name = "some_project"
    source = dict()
    source["type"] = "S3"
    # repository location for S3
    source["location"] = "bucketname/path/file.zip"
    artifacts = {"type": "NO_ARTIFACTS"}

    environment = dict()
    environment["type"] = "LINUX_CONTAINER"
    environment["image"] = "contents_not_validated"
    environment["computeType"] = "BUILD_GENERAL1_SMALL"
    service_role = (
        f"arn:aws:iam::{ACCOUNT_ID}:role/service-role/my-codebuild-service-role"
    )

    client.create_project(
        name=name,
        source=source,
        artifacts=artifacts,
        environment=environment,
        serviceRole=service_role,
    )
    client.start_build(projectName=name)
    response = client.list_builds_for_project(projectName=name)

    assert len(response["ids"]) == 1


# project never started
@mock_aws
def test_codebuild_get_batch_builds_for_project_no_history():
    client = boto3.client("codebuild", region_name="eu-central-1")

    name = "some_project"
    source = dict()
    source["type"] = "S3"
    # repository location for S3
    source["location"] = "bucketname/path/file.zip"
    artifacts = {"type": "NO_ARTIFACTS"}

    environment = dict()
    environment["type"] = "LINUX_CONTAINER"
    environment["image"] = "contents_not_validated"
    environment["computeType"] = "BUILD_GENERAL1_SMALL"
    service_role = (
        f"arn:aws:iam::{ACCOUNT_ID}:role/service-role/my-codebuild-service-role"
    )

    client.create_project(
        name=name,
        source=source,
        artifacts=artifacts,
        environment=environment,
        serviceRole=service_role,
    )

    response = client.list_builds_for_project(projectName=name)
    assert response["ids"] == []

    with pytest.raises(ParamValidationError) as err:
        client.batch_get_builds(ids=response["ids"])
    assert err.typename == "ParamValidationError"


@mock_aws
def test_codebuild_start_build_no_project():
    client = boto3.client("codebuild", region_name="eu-central-1")

    name = "some_project"

    with pytest.raises(client.exceptions.from_code("ResourceNotFoundException")) as err:
        client.start_build(projectName=name)
    assert err.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_codebuild_start_build_no_overrides():
    client = boto3.client("codebuild", region_name="eu-central-1")

    name = "some_project"
    source = dict()
    source["type"] = "S3"
    # repository location for S3
    source["location"] = "bucketname/path/file.zip"
    artifacts = {"type": "NO_ARTIFACTS"}

    environment = dict()
    environment["type"] = "LINUX_CONTAINER"
    environment["image"] = "contents_not_validated"
    environment["computeType"] = "BUILD_GENERAL1_SMALL"
    service_role = (
        f"arn:aws:iam::{ACCOUNT_ID}:role/service-role/my-codebuild-service-role"
    )

    client.create_project(
        name=name,
        source=source,
        artifacts=artifacts,
        environment=environment,
        serviceRole=service_role,
    )
    response = client.start_build(projectName=name)

    assert response["build"]["sourceVersion"] == "refs/heads/main"


@mock_aws
def test_codebuild_start_build_multiple_times():
    client = boto3.client("codebuild", region_name="eu-central-1")

    name = "some_project"
    source = dict()
    source["type"] = "S3"
    # repository location for S3
    source["location"] = "bucketname/path/file.zip"
    artifacts = {"type": "NO_ARTIFACTS"}

    environment = dict()
    environment["type"] = "LINUX_CONTAINER"
    environment["image"] = "contents_not_validated"
    environment["computeType"] = "BUILD_GENERAL1_SMALL"
    service_role = (
        f"arn:aws:iam::{ACCOUNT_ID}:role/service-role/my-codebuild-service-role"
    )

    client.create_project(
        name=name,
        source=source,
        artifacts=artifacts,
        environment=environment,
        serviceRole=service_role,
    )

    client.start_build(projectName=name)
    client.start_build(projectName=name)
    client.start_build(projectName=name)

    assert len(client.list_builds()["ids"]) == 3


@mock_aws
def test_codebuild_start_build_with_overrides():
    client = boto3.client("codebuild", region_name="eu-central-1")

    name = "some_project"
    source = dict()
    source["type"] = "S3"
    # repository location for S3
    source["location"] = "bucketname/path/file.zip"
    artifacts = {"type": "NO_ARTIFACTS"}

    environment = dict()
    environment["type"] = "LINUX_CONTAINER"
    environment["image"] = "contents_not_validated"
    environment["computeType"] = "BUILD_GENERAL1_SMALL"
    service_role = (
        f"arn:aws:iam::{ACCOUNT_ID}:role/service-role/my-codebuild-service-role"
    )

    branch_override = "fix/testing"
    artifacts_override = {"type": "NO_ARTIFACTS"}

    client.create_project(
        name=name,
        source=source,
        artifacts=artifacts,
        environment=environment,
        serviceRole=service_role,
    )
    response = client.start_build(
        projectName=name,
        sourceVersion=branch_override,
        artifactsOverride=artifacts_override,
    )

    assert response["build"]["sourceVersion"] == "fix/testing"


@mock_aws
def test_codebuild_batch_get_builds_1_project():
    client = boto3.client("codebuild", region_name="eu-central-1")

    name = "some_project"
    source = dict()
    source["type"] = "S3"
    # repository location for S3
    source["location"] = "bucketname/path/file.zip"
    artifacts = {"type": "NO_ARTIFACTS"}

    environment = dict()
    environment["type"] = "LINUX_CONTAINER"
    environment["image"] = "contents_not_validated"
    environment["computeType"] = "BUILD_GENERAL1_SMALL"
    service_role = (
        f"arn:aws:iam::{ACCOUNT_ID}:role/service-role/my-codebuild-service-role"
    )

    client.create_project(
        name=name,
        source=source,
        artifacts=artifacts,
        environment=environment,
        serviceRole=service_role,
    )
    client.start_build(projectName=name)

    history = client.list_builds_for_project(projectName=name)
    response = client.batch_get_builds(ids=history["ids"])

    assert len(response["builds"]) == 1
    assert response["builds"][0]["currentPhase"] == "COMPLETED"
    assert isinstance(response["builds"][0]["buildNumber"], int)
    assert "phases" in response["builds"][0]
    assert len(response["builds"][0]["phases"]) == 11


@mock_aws
def test_codebuild_batch_get_builds_2_projects():
    client = boto3.client("codebuild", region_name="eu-central-1")

    source = dict()
    source["type"] = "S3"
    # repository location for S3
    source["location"] = "bucketname/path/file.zip"
    artifacts = {"type": "NO_ARTIFACTS"}

    environment = dict()
    environment["type"] = "LINUX_CONTAINER"
    environment["image"] = "contents_not_validated"
    environment["computeType"] = "BUILD_GENERAL1_SMALL"
    service_role = (
        f"arn:aws:iam::{ACCOUNT_ID}:role/service-role/my-codebuild-service-role"
    )

    client.create_project(
        name="project-1",
        source=source,
        artifacts=artifacts,
        environment=environment,
        serviceRole=service_role,
    )
    client.start_build(projectName="project-1")

    client.create_project(
        name="project-2",
        source=source,
        artifacts=artifacts,
        environment=environment,
        serviceRole=service_role,
    )
    client.start_build(projectName="project-2")

    response = client.list_builds()
    assert len(response["ids"]) == 2

    assert "project-1" in response["ids"][0]
    assert "project-2" in response["ids"][1]

    metadata = client.batch_get_builds(ids=response["ids"])["builds"]
    assert len(metadata) == 2

    assert "project-1" in metadata[0]["id"]
    assert "project-2" in metadata[1]["id"]


@mock_aws
def test_codebuild_batch_get_builds_invalid_build_id():
    client = boto3.client("codebuild", region_name="eu-central-1")

    with pytest.raises(client.exceptions.InvalidInputException) as err:
        client.batch_get_builds(ids=[f"some_project{uuid1()}"])
    assert err.value.response["Error"]["Code"] == "InvalidInputException"


@mock_aws
def test_codebuild_batch_get_builds_empty_build_id():
    client = boto3.client("codebuild", region_name="eu-central-1")

    with pytest.raises(ParamValidationError) as err:
        client.batch_get_builds(ids=[])
    assert err.typename == "ParamValidationError"


@mock_aws
def test_codebuild_delete_project():
    client = boto3.client("codebuild", region_name="eu-central-1")

    name = "some_project"
    source = dict()
    source["type"] = "S3"
    # repository location for S3
    source["location"] = "bucketname/path/file.zip"
    artifacts = {"type": "NO_ARTIFACTS"}

    environment = dict()
    environment["type"] = "LINUX_CONTAINER"
    environment["image"] = "contents_not_validated"
    environment["computeType"] = "BUILD_GENERAL1_SMALL"
    service_role = (
        f"arn:aws:iam::{ACCOUNT_ID}:role/service-role/my-codebuild-service-role"
    )

    client.create_project(
        name=name,
        source=source,
        artifacts=artifacts,
        environment=environment,
        serviceRole=service_role,
    )
    client.start_build(projectName=name)

    response = client.list_builds_for_project(projectName=name)
    assert len(response["ids"]) == 1

    client.delete_project(name=name)

    with pytest.raises(ClientError) as err:
        client.list_builds_for_project(projectName=name)
    assert err.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_codebuild_stop_build():
    client = boto3.client("codebuild", region_name="eu-central-1")

    name = "some_project"
    source = dict()
    source["type"] = "S3"
    # repository location for S3
    source["location"] = "bucketname/path/file.zip"
    artifacts = {"type": "NO_ARTIFACTS"}

    environment = dict()
    environment["type"] = "LINUX_CONTAINER"
    environment["image"] = "contents_not_validated"
    environment["computeType"] = "BUILD_GENERAL1_SMALL"
    service_role = (
        f"arn:aws:iam::{ACCOUNT_ID}:role/service-role/my-codebuild-service-role"
    )

    client.create_project(
        name=name,
        source=source,
        artifacts=artifacts,
        environment=environment,
        serviceRole=service_role,
    )
    client.start_build(projectName=name)

    builds = client.list_builds()

    response = client.stop_build(id=builds["ids"][0])
    assert response["build"]["buildStatus"] == "STOPPED"


@mock_aws
def test_codebuild_stop_build_no_build():
    client = boto3.client("codebuild", region_name="eu-central-1")

    with pytest.raises(client.exceptions.ResourceNotFoundException) as err:
        client.stop_build(id=f"some_project:{uuid1()}")
    assert err.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_codebuild_stop_build_bad_uid():
    client = boto3.client("codebuild", region_name="eu-central-1")

    with pytest.raises(client.exceptions.InvalidInputException) as err:
        client.stop_build(id=f"some_project{uuid1()}")
    assert err.value.response["Error"]["Code"] == "InvalidInputException"
