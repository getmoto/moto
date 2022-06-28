import boto3
import sure  # noqa # pylint: disable=unused-import
from moto import mock_codebuild
from moto.core import ACCOUNT_ID
#from botocore.exceptions import ClientError
#import pytest
from pprint import pprint as pp


@mock_codebuild
def test_codebuild_create_project_s3_artifacts():
    client = boto3.client("codebuild", region_name="eu-central-1")

    name="my_project"
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
    service_role = "arn:aws:iam::123456789012:role/service-role/my-codebuild-service-role"

    response = client.create_project(name=name, source=source, artifacts=artifacts, environment=environment, serviceRole=service_role)

    response.should_not.be.none
    response["project"].should_not.be.none
    response["project"]["serviceRole"].should_not.be.none
    response["project"]["name"].should_not.be.none

    response["project"]["environment"].should.equal(
        {"computeType": "BUILD_GENERAL1_SMALL",
        "image": "contents_not_validated",
        "type": "LINUX_CONTAINER"}
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

    name="my_project"
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
    service_role = "arn:aws:iam::123456789012:role/service-role/my-codebuild-service-role"

    response = client.create_project(name=name, source=source, artifacts=artifacts, environment=environment, serviceRole=service_role)

    response.should_not.be.none
    response["project"].should_not.be.none
    response["project"]["serviceRole"].should_not.be.none
    response["project"]["name"].should_not.be.none

    response["project"]["environment"].should.equal(
        {"computeType": "BUILD_GENERAL1_SMALL",
        "image": "contents_not_validated",
        "type": "LINUX_CONTAINER"}
        )

    response["project"]["source"].should.equal(
         {"location": "bucketname/path/file.zip", "type": "S3"}
        )

    response["project"]["artifacts"].should.equal(
        {"type": "NO_ARTIFACTS"}
    )

# two projects with the same name?

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
    service_role = "arn:aws:iam::123456789012:role/service-role/my-codebuild-service-role"

    client.create_project(name="project1", source=source, artifacts=artifacts, environment=environment, serviceRole=service_role)
    client.create_project(name="project2", source=source, artifacts=artifacts, environment=environment, serviceRole=service_role)
    
    projects = client.list_projects()

    projects["projects"].should_not.be.none
    projects["projects"].should.equal(['project1', 'project2'])


@mock_codebuild
def test_codebuild_list_builds_for_project_no_history():
    client = boto3.client("codebuild", region_name="eu-central-1")

    name="my_project"
    source = dict()
    source["type"] = "S3"
    # repository location for S3
    source["location"] = "bucketname/path/file.zip"
    artifacts = {"type": "NO_ARTIFACTS"}

    environment = dict()
    environment["type"] = "LINUX_CONTAINER"
    environment["image"] = "contents_not_validated"
    environment["computeType"] = "BUILD_GENERAL1_SMALL"
    service_role = "arn:aws:iam::123456789012:role/service-role/my-codebuild-service-role"

    client.create_project(name=name, source=source, artifacts=artifacts, environment=environment, serviceRole=service_role)
    history = client.list_builds_for_project(projectName=name)

    # no build history if it's never started
    history["ids"].should.be.empty
    

@mock_codebuild
def test_codebuild_list_builds_for_project_with_history():
    client = boto3.client("codebuild", region_name="eu-central-1")

    name="my_project"
    source = dict()
    source["type"] = "S3"
    # repository location for S3
    source["location"] = "bucketname/path/file.zip"
    artifacts = {"type": "NO_ARTIFACTS"}

    environment = dict()
    environment["type"] = "LINUX_CONTAINER"
    environment["image"] = "contents_not_validated"
    environment["computeType"] = "BUILD_GENERAL1_SMALL"
    service_role = "arn:aws:iam::123456789012:role/service-role/my-codebuild-service-role"

    client.create_project(name=name, source=source, artifacts=artifacts, environment=environment, serviceRole=service_role)
    client.start_build(projectName=name)
    response = client.list_builds_for_project(projectName=name)

    response["ids"].should_not.be.empty


# # mock start_build() here with hsitroy single projects single build history WILL FAIL WITH non-existent project name
@mock_codebuild
def test_codebuild_start_build_no_overrides():

    client = boto3.client("codebuild", region_name="eu-central-1")
    
    name="my_project"
    source = dict()
    source["type"] = "S3"
    # repository location for S3
    source["location"] = "bucketname/path/file.zip"
    artifacts = {"type": "NO_ARTIFACTS"}

    environment = dict()
    environment["type"] = "LINUX_CONTAINER"
    environment["image"] = "contents_not_validated"
    environment["computeType"] = "BUILD_GENERAL1_SMALL"
    service_role = "arn:aws:iam::123456789012:role/service-role/my-codebuild-service-role"

    client.create_project(name=name, source=source, artifacts=artifacts, environment=environment, serviceRole=service_role)
    response = client.start_build(projectName=name)

    response.should_not.be.none
    response["build"].should_not.be.none
    response["build"]["sourceVersion"].should.equal("refs/heads/main")
    # must test for default artifacts here 

@mock_codebuild
def test_codebuild_start_build_with_overrides():

    client = boto3.client("codebuild", region_name="eu-central-1")
    
    name="my_project"
    source = dict()
    source["type"] = "S3"
    # repository location for S3
    source["location"] = "bucketname/path/file.zip"
    artifacts = {"type": "NO_ARTIFACTS"}

    environment = dict()
    environment["type"] = "LINUX_CONTAINER"
    environment["image"] = "contents_not_validated"
    environment["computeType"] = "BUILD_GENERAL1_SMALL"
    service_role = "arn:aws:iam::123456789012:role/service-role/my-codebuild-service-role"

    branch_override = "fix/testing"
    artifacts_override = {"type": "NO_ARTIFACTS"}

    client.create_project(name=name, source=source, artifacts=artifacts, environment=environment, serviceRole=service_role)
    response = client.start_build(projectName=name, sourceVersion=branch_override, artifactsOverride=artifacts_override)

    response.should_not.be.none
    response["build"].should_not.be.none
    response["build"]["sourceVersion"].should.equal("fix/testing")

    # this is not overriding the artifacts, this must be fixed
    #response["build"]["artifacts"].should.equal({"type": "NO_ARTIFACTS"})

@mock_codebuild
def test_codebuild_batch_get_builds_1_project():
    client = boto3.client("codebuild", region_name="eu-central-1")

    name="my_project"
    source = dict()
    source["type"] = "S3"
    # repository location for S3
    source["location"] = "bucketname/path/file.zip"
    artifacts = {"type": "NO_ARTIFACTS"}

    environment = dict()
    environment["type"] = "LINUX_CONTAINER"
    environment["image"] = "contents_not_validated"
    environment["computeType"] = "BUILD_GENERAL1_SMALL"
    service_role = "arn:aws:iam::123456789012:role/service-role/my-codebuild-service-role"

    branch_override = "fix/testing"
    artifacts_override = {"type": "NO_ARTIFACTS"}
    
    client.create_project(name=name, source=source, artifacts=artifacts, environment=environment, serviceRole=service_role)
    client.start_build(projectName=name, sourceVersion=branch_override, artifactsOverride=artifacts_override)

    history = client.list_builds_for_project(projectName=name)
    response = client.batch_get_builds(ids=history["ids"])

    response.should_not.be.none
    response["builds"].should_not.be.none
    response["builds"][0]["currentPhase"].should.equal("COMPLETED")
    response["builds"][0]["buildNumber"].should.be.a(int)
    response["builds"][0]["phases"].should_not.be.none
    len(response["builds"][0]["phases"]).should.equal(11)
