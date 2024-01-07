import json

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws

# https://docs.aws.amazon.com/systems-manager/latest/userguide/integration-ps-secretsmanager.html


@mock_aws
def test_get_value_from_secrets_manager__by_name():
    # given
    ssm = boto3.client("ssm", "eu-north-1")
    secrets_manager = boto3.client("secretsmanager", "eu-north-1")
    secret_name = "mysecret"
    # when
    secrets_manager.create_secret(Name=secret_name, SecretString="some secret")
    # then
    param = ssm.get_parameter(
        Name=f"/aws/reference/secretsmanager/{secret_name}", WithDecryption=True
    )["Parameter"]
    assert param["Name"] == "mysecret"
    assert param["Type"] == "SecureString"
    assert param["Value"] == "some secret"
    assert param["Version"] == 0
    assert "SourceResult" in param

    secret = secrets_manager.describe_secret(SecretId=secret_name)
    source_result = json.loads(param["SourceResult"])

    assert source_result["ARN"] == secret["ARN"]
    assert source_result["Name"] == secret["Name"]
    assert source_result["VersionIdsToStages"] == secret["VersionIdsToStages"]


@mock_aws
def test_get_value_from_secrets_manager__without_decryption():
    # Note that the parameter does not need to exist
    ssm = boto3.client("ssm", "eu-north-1")
    with pytest.raises(ClientError) as exc:
        ssm.get_parameter(Name="/aws/reference/secretsmanager/sth")
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert err["Message"] == (
        "WithDecryption flag must be True for retrieving a Secret Manager secret."
    )


@mock_aws
def test_get_value_from_secrets_manager__with_decryption_false():
    # Note that the parameter does not need to exist
    ssm = boto3.client("ssm", "eu-north-1")
    with pytest.raises(ClientError) as exc:
        ssm.get_parameter(
            Name="/aws/reference/secretsmanager/sth", WithDecryption=False
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert err["Message"] == (
        "WithDecryption flag must be True for retrieving a Secret Manager secret."
    )


@mock_aws
def test_get_value_from_secrets_manager__by_id():
    # given
    ssm = boto3.client("ssm", "eu-north-1")
    secrets_manager = boto3.client("secretsmanager", "eu-north-1")
    name = "mysecret"
    # when
    r1 = secrets_manager.create_secret(Name=name, SecretString="1st")
    version_id1 = r1["VersionId"]
    secrets_manager.put_secret_value(
        SecretId=name, SecretString="2nd", VersionStages=["AWSCURRENT"]
    )
    r3 = secrets_manager.put_secret_value(
        SecretId=name, SecretString="3rd", VersionStages=["ST1"]
    )
    version_id3 = r3["VersionId"]
    # then
    full_name = f"/aws/reference/secretsmanager/{name}:{version_id1}"
    param = ssm.get_parameter(Name=full_name, WithDecryption=True)["Parameter"]
    assert param["Value"] == "1st"

    full_name = f"/aws/reference/secretsmanager/{name}"
    param = ssm.get_parameter(Name=full_name, WithDecryption=True)["Parameter"]
    assert param["Value"] == "2nd"

    full_name = f"/aws/reference/secretsmanager/{name}:{version_id3}"
    param = ssm.get_parameter(Name=full_name, WithDecryption=True)["Parameter"]
    assert param["Value"] == "3rd"


@mock_aws
def test_get_value_from_secrets_manager__by_version():
    # given
    ssm = boto3.client("ssm", "eu-north-1")
    secrets_manager = boto3.client("secretsmanager", "eu-north-1")
    name = "mysecret"
    # when
    secrets_manager.create_secret(Name=name, SecretString="1st")
    secrets_manager.put_secret_value(
        SecretId=name, SecretString="2nd", VersionStages=["AWSCURRENT"]
    )
    # then
    full_name = f"/aws/reference/secretsmanager/{name}:AWSPREVIOUS"
    param = ssm.get_parameter(Name=full_name, WithDecryption=True)["Parameter"]
    assert param["Value"] == "1st"


@mock_aws
def test_get_value_from_secrets_manager__param_does_not_exist():
    ssm = boto3.client("ssm", "us-east-1")
    with pytest.raises(ClientError) as exc:
        ssm.get_parameter(
            Name="/aws/reference/secretsmanager/test", WithDecryption=True
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ParameterNotFound"
    assert err["Message"] == (
        "An error occurred (ParameterNotFound) when referencing Secrets "
        "Manager: Secret /aws/reference/secretsmanager/test not found."
    )
