import boto3
import sure  # noqa # pylint: disable=unused-import
from moto import mock_codebuild
from moto.core import ACCOUNT_ID
from botocore.exceptions import ClientError, ParamValidationError
from uuid import uuid1
import pytest


@mock_codebuild
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
        "arn:aws:iam::{0}:role/service-role/my-codebuild-service-role".format(
            ACCOUNT_ID
        )
    )

    response = client.create_project(
        name=name,
        source=source,
        artifacts=artifacts,
        environment=environment,
        serviceRole=service_role,
    )

    response.should_not.be.none
    response["project"].should_not.be.none
    response["project"]["serviceRole"].should_not.be.none
    response["project"]["name"].should_not.be.none

    response["project"]["environment"].should.equal(
        {
            "computeType": "BUILD_GENERAL1_SMALL",
            "image": "contents_not_validated",
            "type": "LINUX_CONTAINER",
        }
    )

    response["project"]["source"].should.equal(
        {"location": "bucketname/path/file.zip", "type": "S3"}
    )

    response["project"]["artifacts"].should.equal(
        {"location": "bucketname", "type": "S3"}
    )


@mock_codebuild
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
        "arn:aws:iam::{0}:role/service-role/my-codebuild-service-role".format(
            ACCOUNT_ID
        )
    )

    response = client.create_project(
        name=name,
        source=source,
        artifacts=artifacts,
        environment=environment,
        serviceRole=service_role,
    )

    response.should_not.be.none
    response["project"].should_not.be.none
    response["project"]["serviceRole"].should_not.be.none
    response["project"]["name"].should_not.be.none

    response["project"]["environment"].should.equal(
        {
            "computeType": "BUILD_GENERAL1_SMALL",
            "image": "contents_not_validated",
            "type": "LINUX_CONTAINER",
        }
    )

    response["project"]["source"].should.equal(
        {"location": "bucketname/path/file.zip", "type": "S3"}
    )

    response["project"]["artifacts"].should.equal({"type": "NO_ARTIFACTS"})


@mock_codebuild
def test_codebuild_create_project_with_invalid_name():
    client = boto3.client("codebuild", region_name="eu-central-1")

    name = "!some_project"
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
        "arn:aws:iam::{0}:role/service-role/my-codebuild-service-role".format(
            ACCOUNT_ID
        )
    )

    with pytest.raises(client.exceptions.from_code("InvalidInputException")) as err:
        client.create_project(
            name=name,
            source=source,
            artifacts=artifacts,
            environment=environment,
            serviceRole=service_role,
        )
    err.value.response["Error"]["Code"].should.equal("InvalidInputException")


@mock_codebuild
def test_codebuild_create_project_with_invalid_name_length():
    client = boto3.client("codebuild", region_name="eu-central-1")

    name = "some_project_" * 12
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
        "arn:aws:iam::{0}:role/service-role/my-codebuild-service-role".format(
            ACCOUNT_ID
        )
    )

    with pytest.raises(client.exceptions.from_code("InvalidInputException")) as err:
        client.create_project(
            name=name,
            source=source,
            artifacts=artifacts,
            environment=environment,
            serviceRole=service_role,
        )
    err.value.response["Error"]["Code"].should.equal("InvalidInputException")


@mock_codebuild
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
        "arn:aws:iam::{0}:role/service-role/my-codebuild-service-role".format(
            ACCOUNT_ID
        )
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
    err.value.response["Error"]["Code"].should.equal("ResourceAlreadyExistsException")


@mock_codebuild
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
        "arn:aws:iam::{0}:role/service-role/my-codebuild-service-role".format(
            ACCOUNT_ID
        )
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

    projects["projects"].should_not.be.none
    projects["projects"].should.equal(["project1", "project2"])


@mock_codebuild
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
        "arn:aws:iam::{0}:role/service-role/my-codebuild-service-role".format(
            ACCOUNT_ID
        )
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
    history["ids"].should.be.empty


@mock_codebuild
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
        "arn:aws:iam::{0}:role/service-role/my-codebuild-service-role".format(
            ACCOUNT_ID
        )
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

    response["ids"].should_not.be.empty


# project never started
@mock_codebuild
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
        "arn:aws:iam::{0}:role/service-role/my-codebuild-service-role".format(
            ACCOUNT_ID
        )
    )

    client.create_project(
        name=name,
        source=source,
        artifacts=artifacts,
        environment=environment,
        serviceRole=service_role,
    )

    response = client.list_builds_for_project(projectName=name)
    response.should_not.be.none
    response["ids"].should.be.empty

    with pytest.raises(ParamValidationError) as err:
        client.batch_get_builds(ids=response["ids"])
    err.typename.should.equal("ParamValidationError")


@mock_codebuild
def test_codebuild_start_build_no_project():

    client = boto3.client("codebuild", region_name="eu-central-1")

    name = "some_project"

    with pytest.raises(client.exceptions.from_code("ResourceNotFoundException")) as err:
        client.start_build(projectName=name)
    err.value.response["Error"]["Code"].should.equal("ResourceNotFoundException")


@mock_codebuild
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
        "arn:aws:iam::{0}:role/service-role/my-codebuild-service-role".format(
            ACCOUNT_ID
        )
    )

    client.create_project(
        name=name,
        source=source,
        artifacts=artifacts,
        environment=environment,
        serviceRole=service_role,
    )
    response = client.start_build(projectName=name)

    response.should_not.be.none
    response["build"].should_not.be.none
    response["build"]["sourceVersion"].should.equal("refs/heads/main")


@mock_codebuild
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
        "arn:aws:iam::{0}:role/service-role/my-codebuild-service-role".format(
            ACCOUNT_ID
        )
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

    len(client.list_builds()["ids"]).should.equal(3)


@mock_codebuild
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
        "arn:aws:iam::{0}:role/service-role/my-codebuild-service-role".format(
            ACCOUNT_ID
        )
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

    response.should_not.be.none
    response["build"].should_not.be.none
    response["build"]["sourceVersion"].should.equal("fix/testing")


@mock_codebuild
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
        "arn:aws:iam::{0}:role/service-role/my-codebuild-service-role".format(
            ACCOUNT_ID
        )
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

    response.should_not.be.none
    response["builds"].should_not.be.none
    response["builds"][0]["currentPhase"].should.equal("COMPLETED")
    response["builds"][0]["buildNumber"].should.be.a(int)
    response["builds"][0]["phases"].should_not.be.none
    len(response["builds"][0]["phases"]).should.equal(11)


@mock_codebuild
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
        "arn:aws:iam::{0}:role/service-role/my-codebuild-service-role".format(
            ACCOUNT_ID
        )
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
    response["ids"].should_not.be.empty

    "project-1".should.be.within(response["ids"][0])
    "project-2".should.be.within(response["ids"][1])

    metadata = client.batch_get_builds(ids=response["ids"])["builds"]
    metadata.should_not.be.none
    "project-1".should.be.within(metadata[0]["id"])
    "project-2".should.be.within(metadata[1]["id"])


@mock_codebuild
def test_codebuild_batch_get_builds_invalid_build_id():
    client = boto3.client("codebuild", region_name="eu-central-1")

    with pytest.raises(client.exceptions.InvalidInputException) as err:
        client.batch_get_builds(ids=["some_project{}".format(uuid1())])
    err.value.response["Error"]["Code"].should.equal("InvalidInputException")


@mock_codebuild
def test_codebuild_batch_get_builds_empty_build_id():
    client = boto3.client("codebuild", region_name="eu-central-1")

    with pytest.raises(ParamValidationError) as err:
        client.batch_get_builds(ids=[])
    err.typename.should.equal("ParamValidationError")


@mock_codebuild
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
        "arn:aws:iam::{0}:role/service-role/my-codebuild-service-role".format(
            ACCOUNT_ID
        )
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
    response["ids"].should_not.be.empty

    client.delete_project(name=name)

    with pytest.raises(ClientError) as err:
        client.list_builds_for_project(projectName=name)
    err.value.response["Error"]["Code"].should.equal("ResourceNotFoundException")


@mock_codebuild
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
        "arn:aws:iam::{0}:role/service-role/my-codebuild-service-role".format(
            ACCOUNT_ID
        )
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
    response["build"]["buildStatus"].should.equal("STOPPED")


@mock_codebuild
def test_codebuild_stop_build_no_build():
    client = boto3.client("codebuild", region_name="eu-central-1")

    with pytest.raises(client.exceptions.ResourceNotFoundException) as err:
        client.stop_build(id="some_project:{0}".format(uuid1()))
    err.value.response["Error"]["Code"].should.equal("ResourceNotFoundException")


@mock_codebuild
def test_codebuild_stop_build_bad_uid():
    client = boto3.client("codebuild", region_name="eu-central-1")

    with pytest.raises(client.exceptions.InvalidInputException) as err:
        client.stop_build(id="some_project{0}".format(uuid1()))
    err.value.response["Error"]["Code"].should.equal("InvalidInputException")
