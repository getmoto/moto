import os

import boto3
from dateutil.tz import tzlocal
import re

from moto import mock_secretsmanager, mock_lambda, settings
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from botocore.exceptions import ClientError, ParamValidationError
import string
import pytz
from freezegun import freeze_time
from datetime import timedelta, datetime
import sure  # noqa # pylint: disable=unused-import
from uuid import uuid4
import pytest

DEFAULT_SECRET_NAME = "test-secret"


@mock_secretsmanager
def test_get_secret_value():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    conn.create_secret(Name="java-util-test-password", SecretString="foosecret")
    result = conn.get_secret_value(SecretId="java-util-test-password")
    assert result["SecretString"] == "foosecret"


@mock_secretsmanager
def test_secret_arn():
    region = "us-west-2"
    conn = boto3.client("secretsmanager", region_name=region)

    create_dict = conn.create_secret(
        Name=DEFAULT_SECRET_NAME,
        SecretString="secret_string",
    )
    assert re.match(
        f"arn:aws:secretsmanager:{region}:{ACCOUNT_ID}:secret:{DEFAULT_SECRET_NAME}-"
        + r"\w{6}",
        create_dict["ARN"],
    )


@mock_secretsmanager
def test_create_secret_with_client_request_token():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    version_id = "eb41453f-25bb-4025-b7f4-850cfca0ce71"
    create_dict = conn.create_secret(
        Name=DEFAULT_SECRET_NAME,
        SecretString="secret_string",
        ClientRequestToken=version_id,
    )
    assert create_dict
    assert create_dict["VersionId"] == version_id


@mock_secretsmanager
def test_get_secret_value_by_arn():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    name = "java-util-test-password"
    secret_value = "test_get_secret_value_by_arn"
    result = conn.create_secret(Name=name, SecretString=secret_value)
    arn = result["ARN"]
    arn.should.match(f"^arn:aws:secretsmanager:us-west-2:{ACCOUNT_ID}:secret:{name}")

    result = conn.get_secret_value(SecretId=arn)
    assert result["SecretString"] == secret_value


@mock_secretsmanager
def test_get_secret_value_binary():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    conn.create_secret(Name="java-util-test-password", SecretBinary=b"foosecret")
    result = conn.get_secret_value(SecretId="java-util-test-password")
    assert result["SecretBinary"] == b"foosecret"


@mock_secretsmanager
def test_get_secret_that_does_not_exist():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    with pytest.raises(ClientError) as cm:
        conn.get_secret_value(SecretId="i-dont-exist")

    assert (
        "Secrets Manager can't find the specified secret."
        == cm.value.response["Error"]["Message"]
    )


@mock_secretsmanager
def test_get_secret_that_does_not_match():
    conn = boto3.client("secretsmanager", region_name="us-west-2")
    conn.create_secret(Name="java-util-test-password", SecretString="foosecret")

    with pytest.raises(ClientError) as cm:
        conn.get_secret_value(SecretId="i-dont-match")

    assert (
        "Secrets Manager can't find the specified secret."
        == cm.value.response["Error"]["Message"]
    )


@mock_secretsmanager
def test_get_secret_value_that_is_marked_deleted():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    conn.create_secret(Name="test-secret", SecretString="foosecret")

    conn.delete_secret(SecretId="test-secret")

    with pytest.raises(ClientError):
        conn.get_secret_value(SecretId="test-secret")


@mock_secretsmanager
def test_get_secret_that_has_no_value():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    conn.create_secret(Name="java-util-test-password")

    with pytest.raises(ClientError) as cm:
        conn.get_secret_value(SecretId="java-util-test-password")

    assert (
        "Secrets Manager can't find the specified secret value for staging label: AWSCURRENT"
        == cm.value.response["Error"]["Message"]
    )


@mock_secretsmanager
def test_get_secret_version_that_does_not_exist():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    result = conn.create_secret(Name="java-util-test-password")
    secret_arn = result["ARN"]
    missing_version_id = "00000000-0000-0000-0000-000000000000"

    with pytest.raises(ClientError) as cm:
        conn.get_secret_value(SecretId=secret_arn, VersionId=missing_version_id)

    assert (
        "An error occurred (ResourceNotFoundException) when calling the GetSecretValue operation: Secrets "
        "Manager can't find the specified secret value for VersionId: 00000000-0000-0000-0000-000000000000"
    ) == cm.value.response["Error"]["Message"]


@mock_secretsmanager
def test_get_secret_version_stage_mismatch():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    result = conn.create_secret(Name="test-secret", SecretString="secret")
    secret_arn = result["ARN"]

    rotated_secret = conn.rotate_secret(
        SecretId=secret_arn, RotationRules={"AutomaticallyAfterDays": 42}
    )

    desc_secret = conn.describe_secret(SecretId=secret_arn)
    versions_to_stages = desc_secret["VersionIdsToStages"]
    version_for_test = rotated_secret["VersionId"]
    stages_for_version = versions_to_stages[version_for_test]

    assert "AWSPENDING" not in stages_for_version
    with pytest.raises(ClientError) as cm:
        conn.get_secret_value(
            SecretId=secret_arn, VersionId=version_for_test, VersionStage="AWSPENDING"
        )

    assert (
        "You provided a VersionStage that is not associated to the provided VersionId."
    ) == cm.value.response["Error"]["Message"]


@mock_secretsmanager
def test_create_secret():
    conn = boto3.client("secretsmanager", region_name="us-east-1")

    result = conn.create_secret(Name="test-secret", SecretString="foosecret")
    assert result["ARN"]
    assert result["Name"] == "test-secret"
    secret = conn.get_secret_value(SecretId="test-secret")
    assert secret["SecretString"] == "foosecret"


@mock_secretsmanager
def test_create_secret_with_tags():
    conn = boto3.client("secretsmanager", region_name="us-east-1")
    secret_name = "test-secret-with-tags"

    result = conn.create_secret(
        Name=secret_name,
        SecretString="foosecret",
        Tags=[{"Key": "Foo", "Value": "Bar"}, {"Key": "Mykey", "Value": "Myvalue"}],
    )
    assert result["ARN"]
    assert result["Name"] == secret_name
    secret_value = conn.get_secret_value(SecretId=secret_name)
    assert secret_value["SecretString"] == "foosecret"
    secret_details = conn.describe_secret(SecretId=secret_name)
    assert secret_details["Tags"] == [
        {"Key": "Foo", "Value": "Bar"},
        {"Key": "Mykey", "Value": "Myvalue"},
    ]


@mock_secretsmanager
def test_create_secret_with_description():
    conn = boto3.client("secretsmanager", region_name="us-east-1")
    secret_name = "test-secret-with-tags"

    result = conn.create_secret(
        Name=secret_name, SecretString="foosecret", Description="desc"
    )
    assert result["ARN"]
    assert result["Name"] == secret_name
    secret_value = conn.get_secret_value(SecretId=secret_name)
    assert secret_value["SecretString"] == "foosecret"
    secret_details = conn.describe_secret(SecretId=secret_name)
    assert secret_details["Description"] == "desc"


@mock_secretsmanager
def test_create_secret_with_tags_and_description():
    conn = boto3.client("secretsmanager", region_name="us-east-1")
    secret_name = "test-secret-with-tags"

    result = conn.create_secret(
        Name=secret_name,
        SecretString="foosecret",
        Description="desc",
        Tags=[{"Key": "Foo", "Value": "Bar"}, {"Key": "Mykey", "Value": "Myvalue"}],
    )
    assert result["ARN"]
    assert result["Name"] == secret_name
    secret_value = conn.get_secret_value(SecretId=secret_name)
    assert secret_value["SecretString"] == "foosecret"
    secret_details = conn.describe_secret(SecretId=secret_name)
    assert secret_details["Tags"] == [
        {"Key": "Foo", "Value": "Bar"},
        {"Key": "Mykey", "Value": "Myvalue"},
    ]
    assert secret_details["Description"] == "desc"


@mock_secretsmanager
def test_delete_secret():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    conn.create_secret(Name="test-secret", SecretString="foosecret")

    deleted_secret = conn.delete_secret(SecretId="test-secret")

    assert deleted_secret["ARN"]
    assert deleted_secret["Name"] == "test-secret"
    assert deleted_secret["DeletionDate"] > datetime.fromtimestamp(1, pytz.utc)

    secret_details = conn.describe_secret(SecretId="test-secret")

    assert secret_details["ARN"]
    assert secret_details["Name"] == "test-secret"
    assert secret_details["DeletedDate"] > datetime.fromtimestamp(1, pytz.utc)


@mock_secretsmanager
def test_delete_secret_by_arn():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    secret = conn.create_secret(Name="test-secret", SecretString="foosecret")

    deleted_secret = conn.delete_secret(SecretId=secret["ARN"])

    assert deleted_secret["ARN"] == secret["ARN"]
    assert deleted_secret["Name"] == "test-secret"
    assert deleted_secret["DeletionDate"] > datetime.fromtimestamp(1, pytz.utc)

    secret_details = conn.describe_secret(SecretId="test-secret")

    assert secret_details["ARN"] == secret["ARN"]
    assert secret_details["Name"] == "test-secret"
    assert secret_details["DeletedDate"] > datetime.fromtimestamp(1, pytz.utc)


@mock_secretsmanager
def test_delete_secret_force():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    conn.create_secret(Name="test-secret", SecretString="foosecret")

    result = conn.delete_secret(SecretId="test-secret", ForceDeleteWithoutRecovery=True)

    assert result["ARN"]
    assert result["DeletionDate"] > datetime.fromtimestamp(1, pytz.utc)
    assert result["Name"] == "test-secret"

    with pytest.raises(ClientError):
        result = conn.get_secret_value(SecretId="test-secret")


@mock_secretsmanager
def test_delete_secret_force_no_such_secret():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    deleted_secret = conn.delete_secret(
        SecretId=DEFAULT_SECRET_NAME, ForceDeleteWithoutRecovery=True
    )
    assert deleted_secret
    assert deleted_secret["Name"] == DEFAULT_SECRET_NAME


@mock_secretsmanager
def test_delete_secret_force_with_arn():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    create_secret = conn.create_secret(Name="test-secret", SecretString="foosecret")

    result = conn.delete_secret(
        SecretId=create_secret["ARN"], ForceDeleteWithoutRecovery=True
    )

    assert result["ARN"]
    assert result["DeletionDate"] > datetime.fromtimestamp(1, pytz.utc)
    assert result["Name"] == "test-secret"

    with pytest.raises(ClientError):
        result = conn.get_secret_value(SecretId="test-secret")


@mock_secretsmanager
def test_delete_secret_that_does_not_exist():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    with pytest.raises(ClientError):
        conn.delete_secret(SecretId="i-dont-exist")


@mock_secretsmanager
def test_delete_secret_fails_with_both_force_delete_flag_and_recovery_window_flag():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    conn.create_secret(Name="test-secret", SecretString="foosecret")

    with pytest.raises(ClientError):
        conn.delete_secret(
            SecretId="test-secret",
            RecoveryWindowInDays=1,
            ForceDeleteWithoutRecovery=True,
        )


@mock_secretsmanager
def test_delete_secret_recovery_window_too_short():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    conn.create_secret(Name="test-secret", SecretString="foosecret")

    with pytest.raises(ClientError):
        conn.delete_secret(SecretId="test-secret", RecoveryWindowInDays=6)


@mock_secretsmanager
def test_delete_secret_recovery_window_too_long():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    conn.create_secret(Name="test-secret", SecretString="foosecret")

    with pytest.raises(ClientError):
        conn.delete_secret(SecretId="test-secret", RecoveryWindowInDays=31)


@mock_secretsmanager
def test_delete_secret_force_no_such_secret_with_invalid_recovery_window():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    with pytest.raises(ClientError):
        conn.delete_secret(
            SecretId=DEFAULT_SECRET_NAME,
            ForceDeleteWithoutRecovery=True,
            RecoveryWindowInDays=4,
        )


@mock_secretsmanager
def test_delete_secret_that_is_marked_deleted():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    conn.create_secret(Name="test-secret", SecretString="foosecret")

    conn.delete_secret(SecretId="test-secret")

    with pytest.raises(ClientError):
        conn.delete_secret(SecretId="test-secret")


@mock_secretsmanager
def test_get_random_password_default_length():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    random_password = conn.get_random_password()
    assert len(random_password["RandomPassword"]) == 32


@mock_secretsmanager
def test_get_random_password_default_requirements():
    # When require_each_included_type, default true
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    random_password = conn.get_random_password()
    # Should contain lowercase, upppercase, digit, special character
    assert any(c.islower() for c in random_password["RandomPassword"])
    assert any(c.isupper() for c in random_password["RandomPassword"])
    assert any(c.isdigit() for c in random_password["RandomPassword"])
    assert any(c in string.punctuation for c in random_password["RandomPassword"])


@mock_secretsmanager
def test_get_random_password_custom_length():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    random_password = conn.get_random_password(PasswordLength=50)
    assert len(random_password["RandomPassword"]) == 50


@mock_secretsmanager
def test_get_random_exclude_lowercase():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    random_password = conn.get_random_password(PasswordLength=55, ExcludeLowercase=True)
    assert not any(c.islower() for c in random_password["RandomPassword"])


@mock_secretsmanager
def test_get_random_exclude_uppercase():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    random_password = conn.get_random_password(PasswordLength=55, ExcludeUppercase=True)
    assert not any(c.isupper() for c in random_password["RandomPassword"])


@mock_secretsmanager
def test_get_random_exclude_characters_and_symbols():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    random_password = conn.get_random_password(
        PasswordLength=20, ExcludeCharacters="xyzDje@?!."
    )
    assert not any(c in "xyzDje@?!." for c in random_password["RandomPassword"])
    assert len(random_password["RandomPassword"]) == 20


@mock_secretsmanager
def test_get_random_exclude_numbers():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    random_password = conn.get_random_password(PasswordLength=100, ExcludeNumbers=True)
    assert not any(c.isdigit() for c in random_password["RandomPassword"])


@mock_secretsmanager
def test_get_random_exclude_punctuation():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    random_password = conn.get_random_password(
        PasswordLength=100, ExcludePunctuation=True
    )
    assert not any(c in string.punctuation for c in random_password["RandomPassword"])


@mock_secretsmanager
def test_get_random_include_space_false():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    random_password = conn.get_random_password(PasswordLength=300)
    assert not any(c.isspace() for c in random_password["RandomPassword"])


@mock_secretsmanager
def test_get_random_include_space_true():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    random_password = conn.get_random_password(PasswordLength=4, IncludeSpace=True)
    assert any(c.isspace() for c in random_password["RandomPassword"])


@mock_secretsmanager
def test_get_random_require_each_included_type():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    random_password = conn.get_random_password(
        PasswordLength=4, RequireEachIncludedType=True
    )
    assert any(c in string.punctuation for c in random_password["RandomPassword"])
    assert any(c in string.ascii_lowercase for c in random_password["RandomPassword"])
    assert any(c in string.ascii_uppercase for c in random_password["RandomPassword"])
    assert any(c in string.digits for c in random_password["RandomPassword"])


@mock_secretsmanager
def test_get_random_too_short_password():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    with pytest.raises(ClientError):
        conn.get_random_password(PasswordLength=3)


@mock_secretsmanager
def test_get_random_too_long_password():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    with pytest.raises(Exception):
        conn.get_random_password(PasswordLength=5555)


@mock_secretsmanager
def test_describe_secret():
    conn = boto3.client("secretsmanager", region_name="us-west-2")
    conn.create_secret(Name="test-secret", SecretString="foosecret")

    conn.create_secret(Name="test-secret-2", SecretString="barsecret")

    secret_description = conn.describe_secret(SecretId="test-secret")
    secret_description_2 = conn.describe_secret(SecretId="test-secret-2")

    assert secret_description  # Returned dict is not empty
    assert secret_description["Name"] == ("test-secret")
    assert secret_description["ARN"] != ""  # Test arn not empty
    assert secret_description_2["Name"] == ("test-secret-2")
    assert secret_description_2["ARN"] != ""  # Test arn not empty
    assert secret_description["CreatedDate"] <= datetime.now(tz=tzlocal())
    assert secret_description["CreatedDate"] > datetime.fromtimestamp(1, pytz.utc)
    assert secret_description_2["CreatedDate"] <= datetime.now(tz=tzlocal())
    assert secret_description_2["CreatedDate"] > datetime.fromtimestamp(1, pytz.utc)
    assert secret_description["LastChangedDate"] <= datetime.now(tz=tzlocal())
    assert secret_description["LastChangedDate"] > datetime.fromtimestamp(1, pytz.utc)
    assert secret_description_2["LastChangedDate"] <= datetime.now(tz=tzlocal())
    assert secret_description_2["LastChangedDate"] > datetime.fromtimestamp(1, pytz.utc)


@mock_secretsmanager
def test_describe_secret_with_arn():
    conn = boto3.client("secretsmanager", region_name="us-west-2")
    results = conn.create_secret(Name="test-secret", SecretString="foosecret")

    secret_description = conn.describe_secret(SecretId=results["ARN"])

    assert secret_description  # Returned dict is not empty
    secret_description["Name"].should.equal("test-secret")
    secret_description["ARN"].should.equal(results["ARN"])
    conn.list_secrets()["SecretList"][0]["ARN"].should.equal(results["ARN"])


@mock_secretsmanager
def test_describe_secret_with_KmsKeyId():
    conn = boto3.client("secretsmanager", region_name="us-west-2")
    results = conn.create_secret(
        Name="test-secret", SecretString="foosecret", KmsKeyId="dummy_arn"
    )

    secret_description = conn.describe_secret(SecretId=results["ARN"])

    secret_description["KmsKeyId"].should.equal("dummy_arn")
    conn.list_secrets()["SecretList"][0]["KmsKeyId"].should.equal(
        secret_description["KmsKeyId"]
    )


@mock_secretsmanager
def test_describe_secret_that_does_not_exist():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    with pytest.raises(ClientError):
        conn.get_secret_value(SecretId="i-dont-exist")


@mock_secretsmanager
def test_describe_secret_that_does_not_match():
    conn = boto3.client("secretsmanager", region_name="us-west-2")
    conn.create_secret(Name="test-secret", SecretString="foosecret")

    with pytest.raises(ClientError):
        conn.get_secret_value(SecretId="i-dont-match")


@mock_secretsmanager
def test_restore_secret():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    conn.create_secret(Name="test-secret", SecretString="foosecret")

    conn.delete_secret(SecretId="test-secret")

    described_secret_before = conn.describe_secret(SecretId="test-secret")
    assert described_secret_before["DeletedDate"] > datetime.fromtimestamp(1, pytz.utc)

    restored_secret = conn.restore_secret(SecretId="test-secret")
    assert restored_secret["ARN"]
    assert restored_secret["Name"] == "test-secret"

    described_secret_after = conn.describe_secret(SecretId="test-secret")
    assert "DeletedDate" not in described_secret_after


@mock_secretsmanager
def test_restore_secret_that_is_not_deleted():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    conn.create_secret(Name="test-secret", SecretString="foosecret")

    restored_secret = conn.restore_secret(SecretId="test-secret")
    assert restored_secret["ARN"]
    assert restored_secret["Name"] == "test-secret"


@mock_secretsmanager
def test_restore_secret_that_does_not_exist():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    with pytest.raises(ClientError):
        conn.restore_secret(SecretId="i-dont-exist")


@mock_secretsmanager
def test_rotate_secret():
    conn = boto3.client("secretsmanager", region_name="us-west-2")
    conn.create_secret(
        Name=DEFAULT_SECRET_NAME, SecretString="foosecret", Description="foodescription"
    )

    rotated_secret = conn.rotate_secret(SecretId=DEFAULT_SECRET_NAME)

    assert rotated_secret
    assert rotated_secret["ARN"] != ""  # Test arn not empty
    assert rotated_secret["Name"] == DEFAULT_SECRET_NAME
    assert rotated_secret["VersionId"] != ""

    describe_secret = conn.describe_secret(SecretId=DEFAULT_SECRET_NAME)

    assert describe_secret["Description"] == "foodescription"


@mock_secretsmanager
def test_rotate_secret_without_secretstring():
    conn = boto3.client("secretsmanager", region_name="us-west-2")
    conn.create_secret(Name=DEFAULT_SECRET_NAME, Description="foodescription")

    rotated_secret = conn.rotate_secret(SecretId=DEFAULT_SECRET_NAME)

    assert rotated_secret
    assert rotated_secret["ARN"] == rotated_secret["ARN"]
    assert rotated_secret["Name"] == DEFAULT_SECRET_NAME
    assert rotated_secret["VersionId"] == rotated_secret["VersionId"]

    describe_secret = conn.describe_secret(SecretId=DEFAULT_SECRET_NAME)
    assert describe_secret["Description"] == "foodescription"


@mock_secretsmanager
def test_rotate_secret_enable_rotation():
    conn = boto3.client("secretsmanager", region_name="us-west-2")
    conn.create_secret(Name=DEFAULT_SECRET_NAME, SecretString="foosecret")

    initial_description = conn.describe_secret(SecretId=DEFAULT_SECRET_NAME)
    assert initial_description
    assert initial_description["RotationEnabled"] is False
    assert initial_description["RotationRules"]["AutomaticallyAfterDays"] == 0

    conn.rotate_secret(
        SecretId=DEFAULT_SECRET_NAME, RotationRules={"AutomaticallyAfterDays": 42}
    )

    rotated_description = conn.describe_secret(SecretId=DEFAULT_SECRET_NAME)
    assert rotated_description
    assert rotated_description["RotationEnabled"] is True
    assert rotated_description["RotationRules"]["AutomaticallyAfterDays"] == 42


@mock_secretsmanager
def test_rotate_secret_that_is_marked_deleted():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    conn.create_secret(Name="test-secret", SecretString="foosecret")

    conn.delete_secret(SecretId="test-secret")

    with pytest.raises(ClientError):
        conn.rotate_secret(SecretId="test-secret")


@mock_secretsmanager
def test_rotate_secret_that_does_not_exist():
    conn = boto3.client("secretsmanager", "us-west-2")

    with pytest.raises(ClientError):
        conn.rotate_secret(SecretId="i-dont-exist")


@mock_secretsmanager
def test_rotate_secret_that_does_not_match():
    conn = boto3.client("secretsmanager", region_name="us-west-2")
    conn.create_secret(Name="test-secret", SecretString="foosecret")

    with pytest.raises(ClientError):
        conn.rotate_secret(SecretId="i-dont-match")


@mock_secretsmanager
def test_rotate_secret_client_request_token_too_short():
    # Test is intentionally empty. Boto3 catches too short ClientRequestToken
    # and raises ParamValidationError before Moto can see it.
    # test_server actually handles this error.
    assert True


@mock_secretsmanager
def test_rotate_secret_client_request_token_too_long():
    conn = boto3.client("secretsmanager", region_name="us-west-2")
    conn.create_secret(Name=DEFAULT_SECRET_NAME, SecretString="foosecret")

    client_request_token = (
        "ED9F8B6C-85B7-446A-B7E4-38F2A3BEB13C-" "ED9F8B6C-85B7-446A-B7E4-38F2A3BEB13C"
    )
    with pytest.raises(ClientError):
        conn.rotate_secret(
            SecretId=DEFAULT_SECRET_NAME, ClientRequestToken=client_request_token
        )


@mock_secretsmanager
def test_rotate_secret_rotation_lambda_arn_too_long():
    conn = boto3.client("secretsmanager", region_name="us-west-2")
    conn.create_secret(Name=DEFAULT_SECRET_NAME, SecretString="foosecret")

    rotation_lambda_arn = "85B7-446A-B7E4" * 147  # == 2058 characters
    with pytest.raises(ClientError):
        conn.rotate_secret(
            SecretId=DEFAULT_SECRET_NAME, RotationLambdaARN=rotation_lambda_arn
        )


@mock_secretsmanager
def test_rotate_secret_rotation_period_zero():
    # Test is intentionally empty. Boto3 catches zero day rotation period
    # and raises ParamValidationError before Moto can see it.
    # test_server actually handles this error.
    assert True


@mock_secretsmanager
def test_rotate_secret_rotation_period_too_long():
    conn = boto3.client("secretsmanager", region_name="us-west-2")
    conn.create_secret(Name=DEFAULT_SECRET_NAME, SecretString="foosecret")

    rotation_rules = {"AutomaticallyAfterDays": 1001}
    with pytest.raises(ClientError):
        conn.rotate_secret(SecretId=DEFAULT_SECRET_NAME, RotationRules=rotation_rules)


def get_rotation_zip_file():
    from tests.test_awslambda.utilities import _process_lambda

    func_str = """
import boto3
import json

def lambda_handler(event, context):
    arn = event['SecretId']
    token = event['ClientRequestToken']
    step = event['Step']

    client = boto3.client("secretsmanager", region_name="us-west-2", endpoint_url="http://motoserver:5000")
    metadata = client.describe_secret(SecretId=arn)
    value = client.get_secret_value(SecretId=arn, VersionId=token, VersionStage="AWSPENDING")

    if not metadata['RotationEnabled']:
        print("Secret %s is not enabled for rotation." % arn)
        raise ValueError("Secret %s is not enabled for rotation." % arn)
    versions = metadata['VersionIdsToStages']
    if token not in versions:
        print("Secret version %s has no stage for rotation of secret %s." % (token, arn))
        raise ValueError("Secret version %s has no stage for rotation of secret %s." % (token, arn))
    if "AWSCURRENT" in versions[token]:
        print("Secret version %s already set as AWSCURRENT for secret %s." % (token, arn))
        return
    elif "AWSPENDING" not in versions[token]:
        print("Secret version %s not set as AWSPENDING for rotation of secret %s." % (token, arn))
        raise ValueError("Secret version %s not set as AWSPENDING for rotation of secret %s." % (token, arn))

    if step == 'createSecret':
        try:
            client.get_secret_value(SecretId=arn, VersionId=token, VersionStage='AWSPENDING')
        except client.exceptions.ResourceNotFoundException:
            client.put_secret_value(
                SecretId=arn,
                ClientRequestToken=token,
                SecretString=json.dumps({'create': True}),
                VersionStages=['AWSPENDING']
            )

    if step == 'setSecret':
        client.put_secret_value(
            SecretId=arn,
            ClientRequestToken=token,
            SecretString='UpdatedValue',
            VersionStages=["AWSPENDING"]
        )

    elif step == 'finishSecret':
        current_version = next(
            version
            for version, stages in metadata['VersionIdsToStages'].items()
            if 'AWSCURRENT' in stages
        )
        print("current: %s new: %s" % (current_version, token))
        client.update_secret_version_stage(
            SecretId=arn,
            VersionStage='AWSCURRENT',
            MoveToVersionId=token,
            RemoveFromVersionId=current_version
        )
        client.update_secret_version_stage(
            SecretId=arn,
            VersionStage='AWSPENDING',
            RemoveFromVersionId=token
        )
    """
    return _process_lambda(func_str)


if settings.TEST_SERVER_MODE:

    @mock_lambda
    @mock_secretsmanager
    def test_rotate_secret_using_lambda():
        from tests.test_awslambda.utilities import get_role_name

        # Passing a `RotationLambdaARN` value to `rotate_secret` should invoke lambda
        lambda_conn = boto3.client(
            "lambda", region_name="us-west-2", endpoint_url="http://localhost:5000"
        )
        func = lambda_conn.create_function(
            FunctionName="testFunction",
            Runtime="python3.8",
            Role=get_role_name(),
            Handler="lambda_function.lambda_handler",
            Code={"ZipFile": get_rotation_zip_file()},
            Description="Secret rotator",
            Timeout=3,
            MemorySize=128,
            Publish=True,
        )

        secrets_conn = boto3.client(
            "secretsmanager",
            region_name="us-west-2",
            endpoint_url="http://localhost:5000",
        )
        secret = secrets_conn.create_secret(
            Name=DEFAULT_SECRET_NAME, SecretString="InitialValue"
        )
        initial_version = secret["VersionId"]

        rotated_secret = secrets_conn.rotate_secret(
            SecretId=DEFAULT_SECRET_NAME,
            RotationLambdaARN=func["FunctionArn"],
            RotationRules=dict(AutomaticallyAfterDays=30),
        )

        # Ensure we received an updated VersionId from `rotate_secret`
        assert rotated_secret["VersionId"] != initial_version

        updated_secret = secrets_conn.get_secret_value(
            SecretId=DEFAULT_SECRET_NAME, VersionStage="AWSCURRENT"
        )
        rotated_version = updated_secret["VersionId"]

        assert initial_version != rotated_version
        metadata = secrets_conn.describe_secret(SecretId=DEFAULT_SECRET_NAME)
        assert metadata["VersionIdsToStages"][initial_version] == ["AWSPREVIOUS"]
        assert metadata["VersionIdsToStages"][rotated_version] == ["AWSCURRENT"]
        assert updated_secret["SecretString"] == "UpdatedValue"


@mock_secretsmanager
def test_put_secret_value_on_non_existing_secret():
    conn = boto3.client("secretsmanager", region_name="us-west-2")
    with pytest.raises(ClientError) as cm:
        conn.put_secret_value(
            SecretId=DEFAULT_SECRET_NAME,
            SecretString="foosecret",
            VersionStages=["AWSCURRENT"],
        )

    cm.value.response["Error"]["Message"].should.equal(
        "Secrets Manager can't find the specified secret."
    )


@mock_secretsmanager
def test_put_secret_value_puts_new_secret():
    conn = boto3.client("secretsmanager", region_name="us-west-2")
    conn.create_secret(Name=DEFAULT_SECRET_NAME, SecretBinary=b"foosecret")
    put_secret_value_dict = conn.put_secret_value(
        SecretId=DEFAULT_SECRET_NAME,
        SecretString="foosecret",
        VersionStages=["AWSCURRENT"],
    )
    version_id = put_secret_value_dict["VersionId"]

    get_secret_value_dict = conn.get_secret_value(
        SecretId=DEFAULT_SECRET_NAME, VersionId=version_id, VersionStage="AWSCURRENT"
    )

    assert get_secret_value_dict
    assert get_secret_value_dict["SecretString"] == "foosecret"


@mock_secretsmanager
def test_put_secret_binary_value_puts_new_secret():
    conn = boto3.client("secretsmanager", region_name="us-west-2")
    conn.create_secret(Name=DEFAULT_SECRET_NAME, SecretBinary=b"foosecret")
    put_secret_value_dict = conn.put_secret_value(
        SecretId=DEFAULT_SECRET_NAME,
        SecretBinary=b"foosecret",
        VersionStages=["AWSCURRENT"],
    )
    version_id = put_secret_value_dict["VersionId"]

    get_secret_value_dict = conn.get_secret_value(
        SecretId=DEFAULT_SECRET_NAME, VersionId=version_id, VersionStage="AWSCURRENT"
    )

    assert get_secret_value_dict
    assert get_secret_value_dict["SecretBinary"] == b"foosecret"


@mock_secretsmanager
def test_create_and_put_secret_binary_value_puts_new_secret():
    conn = boto3.client("secretsmanager", region_name="us-west-2")
    conn.create_secret(Name=DEFAULT_SECRET_NAME, SecretBinary=b"foosecret")
    conn.put_secret_value(
        SecretId=DEFAULT_SECRET_NAME, SecretBinary=b"foosecret_update"
    )

    latest_secret = conn.get_secret_value(SecretId=DEFAULT_SECRET_NAME)

    assert latest_secret
    assert latest_secret["SecretBinary"] == b"foosecret_update"


@mock_secretsmanager
def test_put_secret_binary_requires_either_string_or_binary():
    conn = boto3.client("secretsmanager", region_name="us-west-2")
    with pytest.raises(ClientError) as ire:
        conn.put_secret_value(SecretId=DEFAULT_SECRET_NAME)

    ire.value.response["Error"]["Code"].should.equal("InvalidRequestException")
    ire.value.response["Error"]["Message"].should.equal(
        "You must provide either SecretString or SecretBinary."
    )


@mock_secretsmanager
def test_put_secret_value_can_get_first_version_if_put_twice():
    conn = boto3.client("secretsmanager", region_name="us-west-2")
    conn.create_secret(Name=DEFAULT_SECRET_NAME, SecretBinary=b"foosecret")
    put_secret_value_dict = conn.put_secret_value(
        SecretId=DEFAULT_SECRET_NAME,
        SecretString="first_secret",
        VersionStages=["AWSCURRENT"],
    )
    first_version_id = put_secret_value_dict["VersionId"]
    conn.put_secret_value(
        SecretId=DEFAULT_SECRET_NAME,
        SecretString="second_secret",
        VersionStages=["AWSCURRENT"],
    )

    first_secret_value_dict = conn.get_secret_value(
        SecretId=DEFAULT_SECRET_NAME, VersionId=first_version_id
    )
    first_secret_value = first_secret_value_dict["SecretString"]

    assert first_secret_value == "first_secret"


@mock_secretsmanager
def test_put_secret_value_versions_differ_if_same_secret_put_twice():
    conn = boto3.client("secretsmanager", region_name="us-west-2")
    conn.create_secret(Name=DEFAULT_SECRET_NAME, SecretBinary="foosecret")
    put_secret_value_dict = conn.put_secret_value(
        SecretId=DEFAULT_SECRET_NAME,
        SecretString="dupe_secret",
        VersionStages=["AWSCURRENT"],
    )
    first_version_id = put_secret_value_dict["VersionId"]
    put_secret_value_dict = conn.put_secret_value(
        SecretId=DEFAULT_SECRET_NAME,
        SecretString="dupe_secret",
        VersionStages=["AWSCURRENT"],
    )
    second_version_id = put_secret_value_dict["VersionId"]

    assert first_version_id != second_version_id


@mock_secretsmanager
def test_put_secret_value_maintains_description_and_tags():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    previous_response = conn.create_secret(
        Name=DEFAULT_SECRET_NAME,
        SecretString="foosecret",
        Description="desc",
        Tags=[{"Key": "Foo", "Value": "Bar"}, {"Key": "Mykey", "Value": "Myvalue"}],
    )
    previous_version_id = previous_response["VersionId"]

    conn = boto3.client("secretsmanager", region_name="us-west-2")
    current_response = conn.put_secret_value(
        SecretId=DEFAULT_SECRET_NAME,
        SecretString="dupe_secret",
        VersionStages=["AWSCURRENT"],
    )
    current_version_id = current_response["VersionId"]

    secret_details = conn.describe_secret(SecretId=DEFAULT_SECRET_NAME)
    assert secret_details["Tags"] == [
        {"Key": "Foo", "Value": "Bar"},
        {"Key": "Mykey", "Value": "Myvalue"},
    ]
    assert secret_details["Description"] == "desc"
    assert secret_details["VersionIdsToStages"] is not None
    assert previous_version_id in secret_details["VersionIdsToStages"]
    assert current_version_id in secret_details["VersionIdsToStages"]
    assert secret_details["VersionIdsToStages"][previous_version_id] == ["AWSPREVIOUS"]
    assert secret_details["VersionIdsToStages"][current_version_id] == ["AWSCURRENT"]


@mock_secretsmanager
def test_can_list_secret_version_ids():
    conn = boto3.client("secretsmanager", region_name="us-west-2")
    conn.create_secret(Name=DEFAULT_SECRET_NAME, SecretBinary="foosecret")
    put_secret_value_dict = conn.put_secret_value(
        SecretId=DEFAULT_SECRET_NAME,
        SecretString="dupe_secret",
        VersionStages=["AWSCURRENT"],
    )
    first_version_id = put_secret_value_dict["VersionId"]
    put_secret_value_dict = conn.put_secret_value(
        SecretId=DEFAULT_SECRET_NAME,
        SecretString="dupe_secret",
        VersionStages=["AWSCURRENT"],
    )
    second_version_id = put_secret_value_dict["VersionId"]

    versions_list = conn.list_secret_version_ids(SecretId=DEFAULT_SECRET_NAME)

    returned_version_ids = [v["VersionId"] for v in versions_list["Versions"]]

    assert [first_version_id, second_version_id].sort() == returned_version_ids.sort()


@mock_secretsmanager
def test_put_secret_value_version_stages_response():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    # Creation.
    first_version_id = "eb41453f-25bb-4025-b7f4-850cfca0ce71"
    conn.create_secret(
        Name=DEFAULT_SECRET_NAME,
        SecretString="first_secret_string",
        ClientRequestToken=first_version_id,
    )

    # Use PutSecretValue to push a new version with new version stages.
    second_version_id = "eb41453f-25bb-4025-b7f4-850cfca0ce72"
    second_version_stages = ["SAMPLESTAGE1", "SAMPLESTAGE0"]
    second_put_res_dict = conn.put_secret_value(
        SecretId=DEFAULT_SECRET_NAME,
        SecretString="second_secret_string",
        VersionStages=second_version_stages,
        ClientRequestToken=second_version_id,
    )
    assert second_put_res_dict
    assert second_put_res_dict["VersionId"] == second_version_id
    assert second_put_res_dict["VersionStages"] == second_version_stages


@mock_secretsmanager
def test_put_secret_value_version_stages_pending_response():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    # Creation.
    first_version_id = "eb41453f-25bb-4025-b7f4-850cfca0ce71"
    conn.create_secret(
        Name=DEFAULT_SECRET_NAME,
        SecretString="first_secret_string",
        ClientRequestToken=first_version_id,
    )

    # Use PutSecretValue to push a new version with new version stages.
    second_version_id = "eb41453f-25bb-4025-b7f4-850cfca0ce72"
    second_version_stages = ["AWSPENDING"]
    second_put_res_dict = conn.put_secret_value(
        SecretId=DEFAULT_SECRET_NAME,
        SecretString="second_secret_string",
        VersionStages=second_version_stages,
        ClientRequestToken=second_version_id,
    )
    assert second_put_res_dict
    assert second_put_res_dict["VersionId"] == second_version_id
    assert second_put_res_dict["VersionStages"] == second_version_stages


@mock_secretsmanager
def test_after_put_secret_value_version_stages_can_get_current():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    # Creation.
    first_version_id = "eb41453f-25bb-4025-b7f4-850cfca0ce71"
    first_secret_string = "first_secret_string"
    conn.create_secret(
        Name=DEFAULT_SECRET_NAME,
        SecretString=first_secret_string,
        ClientRequestToken=first_version_id,
    )

    # Use PutSecretValue to push a new version with new version stages.
    second_version_id = "eb41453f-25bb-4025-b7f4-850cfca0ce72"
    conn.put_secret_value(
        SecretId=DEFAULT_SECRET_NAME,
        SecretString="second_secret_string",
        VersionStages=["SAMPLESTAGE1", "SAMPLESTAGE0"],
        ClientRequestToken=second_version_id,
    )

    # Get current.
    get_dict = conn.get_secret_value(SecretId=DEFAULT_SECRET_NAME)
    assert get_dict
    assert get_dict["VersionId"] == first_version_id
    assert get_dict["SecretString"] == first_secret_string
    assert get_dict["VersionStages"] == ["AWSCURRENT"]


@mock_secretsmanager
def test_after_put_secret_value_version_stages_can_get_current_with_custom_version_stage():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    # Creation.
    first_version_id = "eb41453f-25bb-4025-b7f4-850cfca0ce71"
    first_secret_string = "first_secret_string"
    conn.create_secret(
        Name=DEFAULT_SECRET_NAME,
        SecretString=first_secret_string,
        ClientRequestToken=first_version_id,
    )

    # Use PutSecretValue to push a new version with new version stages.
    second_version_id = "eb41453f-25bb-4025-b7f4-850cfca0ce72"
    conn.put_secret_value(
        SecretId=DEFAULT_SECRET_NAME,
        SecretString="second_secret_string",
        VersionStages=["SAMPLESTAGE1", "SAMPLESTAGE0"],
        ClientRequestToken=second_version_id,
    )
    # Create a third version with one of the old stages
    third_version_id = "eb41453f-25bb-4025-b7f4-850cfca0ce73"
    third_secret_string = "third_secret_string"
    conn.put_secret_value(
        SecretId=DEFAULT_SECRET_NAME,
        SecretString=third_secret_string,
        VersionStages=["SAMPLESTAGE1"],
        ClientRequestToken=third_version_id,
    )

    # Get current with the stage label of the third version.
    get_dict = conn.get_secret_value(
        SecretId=DEFAULT_SECRET_NAME, VersionStage="SAMPLESTAGE1"
    )
    versions = conn.list_secret_version_ids(SecretId=DEFAULT_SECRET_NAME)["Versions"]
    versions_by_key = {version["VersionId"]: version for version in versions}
    # Check if indeed the third version is returned
    assert get_dict
    assert get_dict["VersionId"] == third_version_id
    assert get_dict["SecretString"] == third_secret_string
    assert get_dict["VersionStages"] == ["SAMPLESTAGE1"]
    # Check if all the versions have the proper labels
    assert versions_by_key[first_version_id]["VersionStages"] == ["AWSCURRENT"]
    assert versions_by_key[second_version_id]["VersionStages"] == ["SAMPLESTAGE0"]
    assert versions_by_key[third_version_id]["VersionStages"] == ["SAMPLESTAGE1"]


@mock_secretsmanager
def test_after_put_secret_value_version_stages_pending_can_get_current():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    # Creation.
    first_version_id = "eb41453f-25bb-4025-b7f4-850cfca0ce71"
    first_secret_string = "first_secret_string"
    conn.create_secret(
        Name=DEFAULT_SECRET_NAME,
        SecretString=first_secret_string,
        ClientRequestToken=first_version_id,
    )

    # Use PutSecretValue to push a new version with new version stages.
    pending_version_id = "eb41453f-25bb-4025-b7f4-850cfca0ce72"
    conn.put_secret_value(
        SecretId=DEFAULT_SECRET_NAME,
        SecretString="second_secret_string",
        VersionStages=["AWSPENDING"],
        ClientRequestToken=pending_version_id,
    )

    # Get current.
    get_dict = conn.get_secret_value(SecretId=DEFAULT_SECRET_NAME)
    assert get_dict
    assert get_dict["VersionId"] == first_version_id
    assert get_dict["SecretString"] == first_secret_string
    assert get_dict["VersionStages"] == ["AWSCURRENT"]


@mock_secretsmanager
@pytest.mark.parametrize("pass_arn", [True, False])
def test_update_secret(pass_arn):
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    created_secret = conn.create_secret(Name="test-secret", SecretString="foosecret")

    assert created_secret["ARN"]
    assert created_secret["Name"] == "test-secret"
    assert created_secret["VersionId"] != ""

    secret_id = created_secret["ARN"] if pass_arn else "test-secret"

    secret = conn.get_secret_value(SecretId=secret_id)
    assert secret["SecretString"] == "foosecret"

    updated_secret = conn.update_secret(SecretId=secret_id, SecretString="barsecret")

    assert updated_secret["ARN"]
    assert updated_secret["Name"] == "test-secret"
    assert updated_secret["VersionId"] != ""

    secret = conn.get_secret_value(SecretId=secret_id)
    assert secret["SecretString"] == "barsecret"
    assert created_secret["VersionId"] != updated_secret["VersionId"]


@mock_secretsmanager
@pytest.mark.parametrize("pass_arn", [True, False])
def test_update_secret_updates_last_changed_dates(pass_arn):
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    # create a secret
    created_secret = conn.create_secret(Name="test-secret", SecretString="foosecret")
    secret_id = created_secret["ARN"] if pass_arn else "test-secret"

    # save details for secret before modification
    secret_details_1 = conn.describe_secret(SecretId=secret_id)
    # check if only LastChangedDate changed, CreatedDate should stay the same
    with freeze_time(timedelta(minutes=1)):
        conn.update_secret(SecretId="test-secret", Description="new-desc")
        secret_details_2 = conn.describe_secret(SecretId=secret_id)
        assert secret_details_1["CreatedDate"] == secret_details_2["CreatedDate"]
        if os.environ.get("TEST_SERVER_MODE", "false").lower() == "false":
            assert (
                secret_details_1["LastChangedDate"]
                < secret_details_2["LastChangedDate"]
            )
        else:
            # Can't manipulate time in server mode, so use weaker constraints here
            assert (
                secret_details_1["LastChangedDate"]
                <= secret_details_2["LastChangedDate"]
            )


@mock_secretsmanager
def test_update_secret_with_tags_and_description():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    created_secret = conn.create_secret(
        Name="test-secret",
        SecretString="foosecret",
        Description="desc",
        Tags=[{"Key": "Foo", "Value": "Bar"}, {"Key": "Mykey", "Value": "Myvalue"}],
    )

    assert created_secret["ARN"]
    assert created_secret["Name"] == "test-secret"
    assert created_secret["VersionId"] != ""

    secret = conn.get_secret_value(SecretId="test-secret")
    assert secret["SecretString"] == "foosecret"

    updated_secret = conn.update_secret(
        SecretId="test-secret", SecretString="barsecret"
    )

    assert updated_secret["ARN"]
    assert updated_secret["Name"] == "test-secret"
    assert updated_secret["VersionId"] != ""

    secret = conn.get_secret_value(SecretId="test-secret")
    assert secret["SecretString"] == "barsecret"
    assert created_secret["VersionId"] != updated_secret["VersionId"]
    secret_details = conn.describe_secret(SecretId="test-secret")
    assert secret_details["Tags"] == [
        {"Key": "Foo", "Value": "Bar"},
        {"Key": "Mykey", "Value": "Myvalue"},
    ]
    assert secret_details["Description"] == "desc"


@mock_secretsmanager
def test_update_secret_with_KmsKeyId():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    created_secret = conn.create_secret(
        Name="test-secret", SecretString="foosecret", KmsKeyId="foo_arn"
    )

    assert created_secret["ARN"]
    assert created_secret["Name"] == "test-secret"
    assert created_secret["VersionId"] != ""

    secret = conn.get_secret_value(SecretId="test-secret")
    assert secret["SecretString"] == "foosecret"

    secret_details = conn.describe_secret(SecretId="test-secret")
    secret_details["KmsKeyId"].should.equal("foo_arn")

    updated_secret = conn.update_secret(
        SecretId="test-secret", SecretString="barsecret", KmsKeyId="bar_arn"
    )

    assert updated_secret["ARN"]
    assert updated_secret["Name"] == "test-secret"
    assert updated_secret["VersionId"] != ""

    secret = conn.get_secret_value(SecretId="test-secret")
    assert secret["SecretString"] == "barsecret"
    assert created_secret["VersionId"] != updated_secret["VersionId"]

    secret_details = conn.describe_secret(SecretId="test-secret")
    secret_details["KmsKeyId"].should.equal("bar_arn")


@mock_secretsmanager
def test_update_secret_which_does_not_exit():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    with pytest.raises(ClientError) as cm:
        conn.update_secret(SecretId="test-secret", SecretString="barsecret")

    assert (
        "Secrets Manager can't find the specified secret."
        == cm.value.response["Error"]["Message"]
    )


@mock_secretsmanager
def test_update_secret_marked_as_deleted():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    conn.create_secret(Name="test-secret", SecretString="foosecret")
    conn.delete_secret(SecretId="test-secret")

    with pytest.raises(ClientError) as cm:
        conn.update_secret(SecretId="test-secret", SecretString="barsecret")

    assert (
        "because it was marked for deletion." in cm.value.response["Error"]["Message"]
    )


@mock_secretsmanager
def test_update_secret_marked_as_deleted_after_restoring():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    conn.create_secret(Name="test-secret", SecretString="foosecret")
    conn.delete_secret(SecretId="test-secret")
    conn.restore_secret(SecretId="test-secret")

    updated_secret = conn.update_secret(
        SecretId="test-secret", SecretString="barsecret"
    )

    assert updated_secret["ARN"]
    assert updated_secret["Name"] == "test-secret"
    assert updated_secret["VersionId"] != ""


@mock_secretsmanager
@pytest.mark.parametrize("pass_arn", [True, False])
def test_tag_resource(pass_arn):
    conn = boto3.client("secretsmanager", region_name="us-west-2")
    created_secret = conn.create_secret(Name="test-secret", SecretString="foosecret")
    secret_id = created_secret["ARN"] if pass_arn else "test-secret"
    conn.tag_resource(
        SecretId=secret_id, Tags=[{"Key": "FirstTag", "Value": "SomeValue"}]
    )
    conn.tag_resource(
        SecretId="test-secret", Tags=[{"Key": "FirstTag", "Value": "SomeOtherValue"}]
    )
    conn.tag_resource(
        SecretId=secret_id, Tags=[{"Key": "SecondTag", "Value": "AnotherValue"}]
    )

    secrets = conn.list_secrets()
    assert secrets["SecretList"][0].get("Tags") == [
        {"Key": "FirstTag", "Value": "SomeOtherValue"},
        {"Key": "SecondTag", "Value": "AnotherValue"},
    ]

    with pytest.raises(ClientError) as cm:
        conn.tag_resource(
            SecretId="dummy-test-secret",
            Tags=[{"Key": "FirstTag", "Value": "SomeValue"}],
        )

    assert (
        "Secrets Manager can't find the specified secret."
        == cm.value.response["Error"]["Message"]
    )


@mock_secretsmanager
@pytest.mark.parametrize("pass_arn", [True, False])
def test_untag_resource(pass_arn):
    conn = boto3.client("secretsmanager", region_name="us-west-2")
    created_secret = conn.create_secret(Name="test-secret", SecretString="foosecret")
    secret_id = created_secret["ARN"] if pass_arn else "test-secret"
    conn.tag_resource(
        SecretId=secret_id,
        Tags=[
            {"Key": "FirstTag", "Value": "SomeValue"},
            {"Key": "SecondTag", "Value": "SomeValue"},
        ],
    )

    conn.untag_resource(SecretId=secret_id, TagKeys=["FirstTag"])
    secrets = conn.list_secrets()
    assert secrets["SecretList"][0].get("Tags") == [
        {"Key": "SecondTag", "Value": "SomeValue"},
    ]

    with pytest.raises(ClientError) as cm:
        conn.untag_resource(SecretId="dummy-test-secret", TagKeys=["FirstTag"])

    assert (
        "Secrets Manager can't find the specified secret."
        == cm.value.response["Error"]["Message"]
    )


@mock_secretsmanager
def test_secret_versions_to_stages_attribute_discrepancy():
    client = boto3.client("secretsmanager", region_name="us-west-2")

    resp = client.create_secret(Name=DEFAULT_SECRET_NAME, SecretString="foosecret")
    previous_version_id = resp["VersionId"]

    resp = client.put_secret_value(
        SecretId=DEFAULT_SECRET_NAME,
        SecretString="dupe_secret",
        VersionStages=["AWSCURRENT"],
    )
    current_version_id = resp["VersionId"]

    secret = client.describe_secret(SecretId=DEFAULT_SECRET_NAME)
    describe_vtos = secret["VersionIdsToStages"]
    assert describe_vtos[current_version_id] == ["AWSCURRENT"]
    assert describe_vtos[previous_version_id] == ["AWSPREVIOUS"]

    secret = client.list_secrets(
        Filters=[{"Key": "name", "Values": [DEFAULT_SECRET_NAME]}]
    ).get("SecretList")[0]
    list_vtos = secret["SecretVersionsToStages"]
    assert list_vtos[current_version_id] == ["AWSCURRENT"]
    assert list_vtos[previous_version_id] == ["AWSPREVIOUS"]

    assert describe_vtos == list_vtos


@mock_secretsmanager
def test_update_secret_with_client_request_token():
    client = boto3.client("secretsmanager", region_name="us-west-2")
    secret_name = "test-secret"
    client_request_token = str(uuid4())

    client.create_secret(Name=secret_name, SecretString="first-secret")
    updated_secret = client.update_secret(
        SecretId=secret_name,
        SecretString="second-secret",
        ClientRequestToken=client_request_token,
    )
    assert client_request_token == updated_secret["VersionId"]
    updated_secret = client.update_secret(
        SecretId=secret_name, SecretString="third-secret"
    )
    assert client_request_token != updated_secret["VersionId"]
    invalid_request_token = "test-token"
    with pytest.raises(ParamValidationError) as pve:
        client.update_secret(
            SecretId=secret_name,
            SecretString="fourth-secret",
            ClientRequestToken=invalid_request_token,
        )
        pve.value.response["Error"]["Code"].should.equal("InvalidParameterException")
        pve.value.response["Error"]["Message"].should.equal(
            "ClientRequestToken must be 32-64 characters long."
        )
