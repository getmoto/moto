import boto3

import sure  # noqa
from moto import mock_codecommit
from moto.core import ACCOUNT_ID
from botocore.exceptions import ClientError
from nose.tools import assert_raises


@mock_codecommit
def test_create_repository():
    client = boto3.client("codecommit", region_name="eu-central-1")
    response = client.create_repository(
        repositoryName="repository_one", repositoryDescription="description repo one"
    )

    response.should_not.be.none
    response["repositoryMetadata"].should_not.be.none
    response["repositoryMetadata"]["creationDate"].should_not.be.none
    response["repositoryMetadata"]["lastModifiedDate"].should_not.be.none
    response["repositoryMetadata"]["repositoryId"].should_not.be.empty
    response["repositoryMetadata"]["repositoryName"].should.equal("repository_one")
    response["repositoryMetadata"]["repositoryDescription"].should.equal(
        "description repo one"
    )
    response["repositoryMetadata"]["cloneUrlSsh"].should.equal(
        "ssh://git-codecommit.{0}.amazonaws.com/v1/repos/{1}".format(
            "eu-central-1", "repository_one"
        )
    )
    response["repositoryMetadata"]["cloneUrlHttp"].should.equal(
        "https://git-codecommit.{0}.amazonaws.com/v1/repos/{1}".format(
            "eu-central-1", "repository_one"
        )
    )
    response["repositoryMetadata"]["Arn"].should.equal(
        "arn:aws:codecommit:{0}:{1}:{2}".format(
            "eu-central-1", ACCOUNT_ID, "repository_one"
        )
    )
    response["repositoryMetadata"]["accountId"].should.equal(ACCOUNT_ID)


@mock_codecommit
def test_create_repository_without_description():
    client = boto3.client("codecommit", region_name="eu-central-1")

    response = client.create_repository(repositoryName="repository_two")

    response.should_not.be.none
    response.get("repositoryMetadata").should_not.be.none
    response.get("repositoryMetadata").get("repositoryName").should.equal(
        "repository_two"
    )
    response.get("repositoryMetadata").get("repositoryDescription").should.be.none
    response["repositoryMetadata"].should_not.be.none
    response["repositoryMetadata"]["creationDate"].should_not.be.none
    response["repositoryMetadata"]["lastModifiedDate"].should_not.be.none
    response["repositoryMetadata"]["repositoryId"].should_not.be.empty
    response["repositoryMetadata"]["cloneUrlSsh"].should.equal(
        "ssh://git-codecommit.{0}.amazonaws.com/v1/repos/{1}".format(
            "eu-central-1", "repository_two"
        )
    )
    response["repositoryMetadata"]["cloneUrlHttp"].should.equal(
        "https://git-codecommit.{0}.amazonaws.com/v1/repos/{1}".format(
            "eu-central-1", "repository_two"
        )
    )
    response["repositoryMetadata"]["Arn"].should.equal(
        "arn:aws:codecommit:{0}:{1}:{2}".format(
            "eu-central-1", ACCOUNT_ID, "repository_two"
        )
    )
    response["repositoryMetadata"]["accountId"].should.equal(ACCOUNT_ID)


@mock_codecommit
def test_create_repository_repository_name_exists():
    client = boto3.client("codecommit", region_name="eu-central-1")

    client.create_repository(repositoryName="repository_two")

    with assert_raises(ClientError) as e:
        client.create_repository(
            repositoryName="repository_two",
            repositoryDescription="description repo two",
        )
    ex = e.exception
    ex.operation_name.should.equal("CreateRepository")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("RepositoryNameExistsException")
    ex.response["Error"]["Message"].should.equal(
        "Repository named {0} already exists".format("repository_two")
    )


@mock_codecommit
def test_create_repository_invalid_repository_name():
    client = boto3.client("codecommit", region_name="eu-central-1")

    with assert_raises(ClientError) as e:
        client.create_repository(repositoryName="in_123_valid_@#$_characters")
    ex = e.exception
    ex.operation_name.should.equal("CreateRepository")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("InvalidRepositoryNameException")
    ex.response["Error"]["Message"].should.equal(
        "The repository name is not valid. Repository names can be any valid "
        "combination of letters, numbers, "
        "periods, underscores, and dashes between 1 and 100 characters in "
        "length. Names are case sensitive. "
        "For more information, see Limits in the AWS CodeCommit User Guide. "
    )


@mock_codecommit
def test_get_repository():
    client = boto3.client("codecommit", region_name="eu-central-1")

    repository_name = "repository_one"

    client.create_repository(
        repositoryName=repository_name, repositoryDescription="description repo one"
    )

    response = client.get_repository(repositoryName=repository_name)

    response.should_not.be.none
    response.get("repositoryMetadata").should_not.be.none
    response.get("repositoryMetadata").get("creationDate").should_not.be.none
    response.get("repositoryMetadata").get("lastModifiedDate").should_not.be.none
    response.get("repositoryMetadata").get("repositoryId").should_not.be.empty
    response.get("repositoryMetadata").get("repositoryName").should.equal(
        repository_name
    )
    response.get("repositoryMetadata").get("repositoryDescription").should.equal(
        "description repo one"
    )
    response.get("repositoryMetadata").get("cloneUrlSsh").should.equal(
        "ssh://git-codecommit.{0}.amazonaws.com/v1/repos/{1}".format(
            "eu-central-1", "repository_one"
        )
    )
    response.get("repositoryMetadata").get("cloneUrlHttp").should.equal(
        "https://git-codecommit.{0}.amazonaws.com/v1/repos/{1}".format(
            "eu-central-1", "repository_one"
        )
    )
    response.get("repositoryMetadata").get("Arn").should.equal(
        "arn:aws:codecommit:{0}:{1}:{2}".format(
            "eu-central-1", ACCOUNT_ID, "repository_one"
        )
    )
    response.get("repositoryMetadata").get("accountId").should.equal(ACCOUNT_ID)

    client = boto3.client("codecommit", region_name="us-east-1")

    with assert_raises(ClientError) as e:
        client.get_repository(repositoryName=repository_name)
    ex = e.exception
    ex.operation_name.should.equal("GetRepository")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("RepositoryDoesNotExistException")
    ex.response["Error"]["Message"].should.equal(
        "{0} does not exist".format(repository_name)
    )


@mock_codecommit
def test_get_repository_invalid_repository_name():
    client = boto3.client("codecommit", region_name="eu-central-1")

    with assert_raises(ClientError) as e:
        client.get_repository(repositoryName="repository_one-@#@")
    ex = e.exception
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("InvalidRepositoryNameException")
    ex.response["Error"]["Message"].should.equal(
        "The repository name is not valid. Repository names can be any valid "
        "combination of letters, numbers, "
        "periods, underscores, and dashes between 1 and 100 characters in "
        "length. Names are case sensitive. "
        "For more information, see Limits in the AWS CodeCommit User Guide. "
    )


@mock_codecommit
def test_delete_repository():
    client = boto3.client("codecommit", region_name="us-east-1")

    response = client.create_repository(repositoryName="repository_one")

    repository_id_create = response.get("repositoryMetadata").get("repositoryId")

    response = client.delete_repository(repositoryName="repository_one")

    response.get("repositoryId").should_not.be.none
    repository_id_create.should.equal(response.get("repositoryId"))

    response = client.delete_repository(repositoryName="unknown_repository")

    response.get("repositoryId").should.be.none


@mock_codecommit
def test_delete_repository_invalid_repository_name():
    client = boto3.client("codecommit", region_name="us-east-1")

    with assert_raises(ClientError) as e:
        client.delete_repository(repositoryName="_rep@ository_one")
    ex = e.exception
    ex.operation_name.should.equal("DeleteRepository")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("InvalidRepositoryNameException")
    ex.response["Error"]["Message"].should.equal(
        "The repository name is not valid. Repository names can be any valid "
        "combination of letters, numbers, "
        "periods, underscores, and dashes between 1 and 100 characters in "
        "length. Names are case sensitive. "
        "For more information, see Limits in the AWS CodeCommit User Guide. "
    )
