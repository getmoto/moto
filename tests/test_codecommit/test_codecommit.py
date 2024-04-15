import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID


@mock_aws
def test_create_repository():
    client = boto3.client("codecommit", region_name="eu-central-1")
    metadata = client.create_repository(
        repositoryName="repository_one", repositoryDescription="description repo one"
    )["repositoryMetadata"]

    assert metadata["creationDate"] is not None
    assert metadata["lastModifiedDate"] is not None
    assert metadata["repositoryId"] is not None
    assert metadata["repositoryName"] == "repository_one"
    assert metadata["repositoryDescription"] == "description repo one"
    assert (
        metadata["cloneUrlSsh"]
        == "ssh://git-codecommit.eu-central-1.amazonaws.com/v1/repos/repository_one"
    )
    assert (
        metadata["cloneUrlHttp"]
        == "https://git-codecommit.eu-central-1.amazonaws.com/v1/repos/repository_one"
    )
    assert (
        metadata["Arn"]
        == f"arn:aws:codecommit:eu-central-1:{ACCOUNT_ID}:repository_one"
    )
    assert metadata["accountId"] == ACCOUNT_ID


@mock_aws
def test_create_repository_without_description():
    client = boto3.client("codecommit", region_name="eu-central-1")

    metadata = client.create_repository(repositoryName="repository_two")[
        "repositoryMetadata"
    ]

    assert metadata.get("repositoryName") == "repository_two"
    assert metadata.get("repositoryDescription") is None

    assert metadata["creationDate"] is not None
    assert metadata["lastModifiedDate"] is not None
    assert metadata["repositoryId"] is not None
    assert (
        metadata["cloneUrlSsh"]
        == "ssh://git-codecommit.eu-central-1.amazonaws.com/v1/repos/repository_two"
    )
    assert (
        metadata["cloneUrlHttp"]
        == "https://git-codecommit.eu-central-1.amazonaws.com/v1/repos/repository_two"
    )
    assert (
        metadata["Arn"]
        == f"arn:aws:codecommit:eu-central-1:{ACCOUNT_ID}:repository_two"
    )
    assert metadata["accountId"] == ACCOUNT_ID


@mock_aws
def test_create_repository_repository_name_exists():
    client = boto3.client("codecommit", region_name="eu-central-1")

    client.create_repository(repositoryName="repository_two")

    with pytest.raises(ClientError) as e:
        client.create_repository(
            repositoryName="repository_two",
            repositoryDescription="description repo two",
        )
    ex = e.value
    assert ex.operation_name == "CreateRepository"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "RepositoryNameExistsException"
    assert (
        ex.response["Error"]["Message"]
        == "Repository named repository_two already exists"
    )


@mock_aws
def test_create_repository_invalid_repository_name():
    client = boto3.client("codecommit", region_name="eu-central-1")

    with pytest.raises(ClientError) as e:
        client.create_repository(repositoryName="in_123_valid_@#$_characters")
    ex = e.value
    assert ex.operation_name == "CreateRepository"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "InvalidRepositoryNameException"
    assert (
        ex.response["Error"]["Message"]
        == "The repository name is not valid. Repository names can be any valid combination of letters, numbers, periods, underscores, and dashes between 1 and 100 characters in length. Names are case sensitive. For more information, see Limits in the AWS CodeCommit User Guide. "
    )


@mock_aws
def test_get_repository():
    client = boto3.client("codecommit", region_name="eu-central-1")

    repository_name = "repository_one"

    client.create_repository(
        repositoryName=repository_name, repositoryDescription="description repo one"
    )

    metadata = client.get_repository(repositoryName=repository_name)[
        "repositoryMetadata"
    ]

    assert metadata["creationDate"] is not None
    assert metadata["lastModifiedDate"] is not None
    assert metadata["repositoryId"] is not None
    assert metadata["repositoryName"] == repository_name
    assert metadata["repositoryDescription"] == "description repo one"
    assert (
        metadata["cloneUrlSsh"]
        == "ssh://git-codecommit.eu-central-1.amazonaws.com/v1/repos/repository_one"
    )
    assert (
        metadata["cloneUrlHttp"]
        == "https://git-codecommit.eu-central-1.amazonaws.com/v1/repos/repository_one"
    )
    assert (
        metadata["Arn"]
        == f"arn:aws:codecommit:eu-central-1:{ACCOUNT_ID}:repository_one"
    )
    assert metadata["accountId"] == ACCOUNT_ID

    client = boto3.client("codecommit", region_name="us-east-1")

    with pytest.raises(ClientError) as e:
        client.get_repository(repositoryName=repository_name)
    ex = e.value
    assert ex.operation_name == "GetRepository"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "RepositoryDoesNotExistException"
    assert ex.response["Error"]["Message"] == f"{repository_name} does not exist"


@mock_aws
def test_get_repository_invalid_repository_name():
    client = boto3.client("codecommit", region_name="eu-central-1")

    with pytest.raises(ClientError) as e:
        client.get_repository(repositoryName="repository_one-@#@")
    ex = e.value
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "InvalidRepositoryNameException"
    assert (
        ex.response["Error"]["Message"]
        == "The repository name is not valid. Repository names can be any valid combination of letters, numbers, periods, underscores, and dashes between 1 and 100 characters in length. Names are case sensitive. For more information, see Limits in the AWS CodeCommit User Guide. "
    )


@mock_aws
def test_delete_repository():
    client = boto3.client("codecommit", region_name="us-east-1")

    response = client.create_repository(repositoryName="repository_one")

    repository_id_create = response.get("repositoryMetadata").get("repositoryId")

    response = client.delete_repository(repositoryName="repository_one")

    assert response.get("repositoryId") is not None
    assert repository_id_create == response.get("repositoryId")

    response = client.delete_repository(repositoryName="unknown_repository")

    assert response.get("repositoryId") is None


@mock_aws
def test_delete_repository_invalid_repository_name():
    client = boto3.client("codecommit", region_name="us-east-1")

    with pytest.raises(ClientError) as e:
        client.delete_repository(repositoryName="_rep@ository_one")
    ex = e.value
    assert ex.operation_name == "DeleteRepository"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert ex.response["Error"]["Code"] == "InvalidRepositoryNameException"
    assert (
        ex.response["Error"]["Message"]
        == "The repository name is not valid. Repository names can be any valid combination of letters, numbers, periods, underscores, and dashes between 1 and 100 characters in length. Names are case sensitive. For more information, see Limits in the AWS CodeCommit User Guide. "
    )
