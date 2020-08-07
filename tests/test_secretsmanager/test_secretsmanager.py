# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import boto3

from moto import mock_secretsmanager
from botocore.exceptions import ClientError
import string
import pytz
from datetime import datetime
import sure  # noqa
from nose.tools import assert_raises, assert_equal
from six import b

DEFAULT_SECRET_NAME = "test-secret"


@mock_secretsmanager
def test_get_secret_value():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    create_secret = conn.create_secret(
        Name="java-util-test-password", SecretString="foosecret"
    )
    result = conn.get_secret_value(SecretId="java-util-test-password")
    assert result["SecretString"] == "foosecret"


@mock_secretsmanager
def test_get_secret_value_by_arn():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    secret_value = "test_get_secret_value_by_arn"
    result = conn.create_secret(
        Name="java-util-test-password", SecretString=secret_value
    )
    result = conn.get_secret_value(SecretId=result["ARN"])
    assert result["SecretString"] == secret_value


@mock_secretsmanager
def test_get_secret_value_binary():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    create_secret = conn.create_secret(
        Name="java-util-test-password", SecretBinary=b("foosecret")
    )
    result = conn.get_secret_value(SecretId="java-util-test-password")
    assert result["SecretBinary"] == b("foosecret")


@mock_secretsmanager
def test_get_secret_that_does_not_exist():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    with assert_raises(ClientError) as cm:
        result = conn.get_secret_value(SecretId="i-dont-exist")

    assert_equal(
        "Secrets Manager can't find the specified secret.",
        cm.exception.response["Error"]["Message"],
    )


@mock_secretsmanager
def test_get_secret_that_does_not_match():
    conn = boto3.client("secretsmanager", region_name="us-west-2")
    create_secret = conn.create_secret(
        Name="java-util-test-password", SecretString="foosecret"
    )

    with assert_raises(ClientError) as cm:
        result = conn.get_secret_value(SecretId="i-dont-match")

    assert_equal(
        "Secrets Manager can't find the specified secret.",
        cm.exception.response["Error"]["Message"],
    )


@mock_secretsmanager
def test_get_secret_value_that_is_marked_deleted():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    conn.create_secret(Name="test-secret", SecretString="foosecret")

    conn.delete_secret(SecretId="test-secret")

    with assert_raises(ClientError):
        result = conn.get_secret_value(SecretId="test-secret")


@mock_secretsmanager
def test_get_secret_that_has_no_value():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    create_secret = conn.create_secret(Name="java-util-test-password")

    with assert_raises(ClientError) as cm:
        result = conn.get_secret_value(SecretId="java-util-test-password")

    assert_equal(
        "Secrets Manager can't find the specified secret value for staging label: AWSCURRENT",
        cm.exception.response["Error"]["Message"],
    )


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
def test_delete_secret_force():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    conn.create_secret(Name="test-secret", SecretString="foosecret")

    result = conn.delete_secret(SecretId="test-secret", ForceDeleteWithoutRecovery=True)

    assert result["ARN"]
    assert result["DeletionDate"] > datetime.fromtimestamp(1, pytz.utc)
    assert result["Name"] == "test-secret"

    with assert_raises(ClientError):
        result = conn.get_secret_value(SecretId="test-secret")


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

    with assert_raises(ClientError):
        result = conn.get_secret_value(SecretId="test-secret")


@mock_secretsmanager
def test_delete_secret_that_does_not_exist():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    with assert_raises(ClientError):
        result = conn.delete_secret(
            SecretId="i-dont-exist", ForceDeleteWithoutRecovery=True
        )


@mock_secretsmanager
def test_delete_secret_fails_with_both_force_delete_flag_and_recovery_window_flag():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    conn.create_secret(Name="test-secret", SecretString="foosecret")

    with assert_raises(ClientError):
        result = conn.delete_secret(
            SecretId="test-secret",
            RecoveryWindowInDays=1,
            ForceDeleteWithoutRecovery=True,
        )


@mock_secretsmanager
def test_delete_secret_recovery_window_too_short():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    conn.create_secret(Name="test-secret", SecretString="foosecret")

    with assert_raises(ClientError):
        result = conn.delete_secret(SecretId="test-secret", RecoveryWindowInDays=6)


@mock_secretsmanager
def test_delete_secret_recovery_window_too_long():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    conn.create_secret(Name="test-secret", SecretString="foosecret")

    with assert_raises(ClientError):
        result = conn.delete_secret(SecretId="test-secret", RecoveryWindowInDays=31)


@mock_secretsmanager
def test_delete_secret_that_is_marked_deleted():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    conn.create_secret(Name="test-secret", SecretString="foosecret")

    deleted_secret = conn.delete_secret(SecretId="test-secret")

    with assert_raises(ClientError):
        result = conn.delete_secret(SecretId="test-secret")


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
    assert any(c.islower() for c in random_password["RandomPassword"]) == False


@mock_secretsmanager
def test_get_random_exclude_uppercase():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    random_password = conn.get_random_password(PasswordLength=55, ExcludeUppercase=True)
    assert any(c.isupper() for c in random_password["RandomPassword"]) == False


@mock_secretsmanager
def test_get_random_exclude_characters_and_symbols():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    random_password = conn.get_random_password(
        PasswordLength=20, ExcludeCharacters="xyzDje@?!."
    )
    assert any(c in "xyzDje@?!." for c in random_password["RandomPassword"]) == False
    assert len(random_password["RandomPassword"]) == 20


@mock_secretsmanager
def test_get_random_exclude_numbers():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    random_password = conn.get_random_password(PasswordLength=100, ExcludeNumbers=True)
    assert any(c.isdigit() for c in random_password["RandomPassword"]) == False


@mock_secretsmanager
def test_get_random_exclude_punctuation():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    random_password = conn.get_random_password(
        PasswordLength=100, ExcludePunctuation=True
    )
    assert (
        any(c in string.punctuation for c in random_password["RandomPassword"]) == False
    )


@mock_secretsmanager
def test_get_random_include_space_false():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    random_password = conn.get_random_password(PasswordLength=300)
    assert any(c.isspace() for c in random_password["RandomPassword"]) == False


@mock_secretsmanager
def test_get_random_include_space_true():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    random_password = conn.get_random_password(PasswordLength=4, IncludeSpace=True)
    assert any(c.isspace() for c in random_password["RandomPassword"]) == True


@mock_secretsmanager
def test_get_random_require_each_included_type():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    random_password = conn.get_random_password(
        PasswordLength=4, RequireEachIncludedType=True
    )
    assert (
        any(c in string.punctuation for c in random_password["RandomPassword"]) == True
    )
    assert (
        any(c in string.ascii_lowercase for c in random_password["RandomPassword"])
        == True
    )
    assert (
        any(c in string.ascii_uppercase for c in random_password["RandomPassword"])
        == True
    )
    assert any(c in string.digits for c in random_password["RandomPassword"]) == True


@mock_secretsmanager
def test_get_random_too_short_password():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    with assert_raises(ClientError):
        random_password = conn.get_random_password(PasswordLength=3)


@mock_secretsmanager
def test_get_random_too_long_password():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    with assert_raises(Exception):
        random_password = conn.get_random_password(PasswordLength=5555)


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


@mock_secretsmanager
def test_describe_secret_with_arn():
    conn = boto3.client("secretsmanager", region_name="us-west-2")
    results = conn.create_secret(Name="test-secret", SecretString="foosecret")

    secret_description = conn.describe_secret(SecretId=results["ARN"])

    assert secret_description  # Returned dict is not empty
    assert secret_description["Name"] == ("test-secret")
    assert secret_description["ARN"] != results["ARN"]


@mock_secretsmanager
def test_describe_secret_that_does_not_exist():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    with assert_raises(ClientError):
        result = conn.get_secret_value(SecretId="i-dont-exist")


@mock_secretsmanager
def test_describe_secret_that_does_not_match():
    conn = boto3.client("secretsmanager", region_name="us-west-2")
    conn.create_secret(Name="test-secret", SecretString="foosecret")

    with assert_raises(ClientError):
        result = conn.get_secret_value(SecretId="i-dont-match")


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

    with assert_raises(ClientError):
        result = conn.restore_secret(SecretId="i-dont-exist")


@mock_secretsmanager
def test_rotate_secret():
    conn = boto3.client("secretsmanager", region_name="us-west-2")
    conn.create_secret(Name=DEFAULT_SECRET_NAME, SecretString="foosecret")

    rotated_secret = conn.rotate_secret(SecretId=DEFAULT_SECRET_NAME)

    assert rotated_secret
    assert rotated_secret["ARN"] != ""  # Test arn not empty
    assert rotated_secret["Name"] == DEFAULT_SECRET_NAME
    assert rotated_secret["VersionId"] != ""


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

    with assert_raises(ClientError):
        result = conn.rotate_secret(SecretId="test-secret")


@mock_secretsmanager
def test_rotate_secret_that_does_not_exist():
    conn = boto3.client("secretsmanager", "us-west-2")

    with assert_raises(ClientError):
        result = conn.rotate_secret(SecretId="i-dont-exist")


@mock_secretsmanager
def test_rotate_secret_that_does_not_match():
    conn = boto3.client("secretsmanager", region_name="us-west-2")
    conn.create_secret(Name="test-secret", SecretString="foosecret")

    with assert_raises(ClientError):
        result = conn.rotate_secret(SecretId="i-dont-match")


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
    with assert_raises(ClientError):
        result = conn.rotate_secret(
            SecretId=DEFAULT_SECRET_NAME, ClientRequestToken=client_request_token
        )


@mock_secretsmanager
def test_rotate_secret_rotation_lambda_arn_too_long():
    conn = boto3.client("secretsmanager", region_name="us-west-2")
    conn.create_secret(Name=DEFAULT_SECRET_NAME, SecretString="foosecret")

    rotation_lambda_arn = "85B7-446A-B7E4" * 147  # == 2058 characters
    with assert_raises(ClientError):
        result = conn.rotate_secret(
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
    with assert_raises(ClientError):
        result = conn.rotate_secret(
            SecretId=DEFAULT_SECRET_NAME, RotationRules=rotation_rules
        )


@mock_secretsmanager
def test_put_secret_value_puts_new_secret():
    conn = boto3.client("secretsmanager", region_name="us-west-2")
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
    put_secret_value_dict = conn.put_secret_value(
        SecretId=DEFAULT_SECRET_NAME,
        SecretBinary=b("foosecret"),
        VersionStages=["AWSCURRENT"],
    )
    version_id = put_secret_value_dict["VersionId"]

    get_secret_value_dict = conn.get_secret_value(
        SecretId=DEFAULT_SECRET_NAME, VersionId=version_id, VersionStage="AWSCURRENT"
    )

    assert get_secret_value_dict
    assert get_secret_value_dict["SecretBinary"] == b("foosecret")


@mock_secretsmanager
def test_create_and_put_secret_binary_value_puts_new_secret():
    conn = boto3.client("secretsmanager", region_name="us-west-2")
    conn.create_secret(Name=DEFAULT_SECRET_NAME, SecretBinary=b("foosecret"))
    conn.put_secret_value(
        SecretId=DEFAULT_SECRET_NAME, SecretBinary=b("foosecret_update")
    )

    latest_secret = conn.get_secret_value(SecretId=DEFAULT_SECRET_NAME)

    assert latest_secret
    assert latest_secret["SecretBinary"] == b("foosecret_update")


@mock_secretsmanager
def test_put_secret_binary_requires_either_string_or_binary():
    conn = boto3.client("secretsmanager", region_name="us-west-2")
    with assert_raises(ClientError) as ire:
        conn.put_secret_value(SecretId=DEFAULT_SECRET_NAME)

    ire.exception.response["Error"]["Code"].should.equal("InvalidRequestException")
    ire.exception.response["Error"]["Message"].should.equal(
        "You must provide either SecretString or SecretBinary."
    )


@mock_secretsmanager
def test_put_secret_value_can_get_first_version_if_put_twice():
    conn = boto3.client("secretsmanager", region_name="us-west-2")
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
def test_update_secret():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    created_secret = conn.create_secret(Name="test-secret", SecretString="foosecret")

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
def test_update_secret_which_does_not_exit():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    with assert_raises(ClientError) as cm:
        updated_secret = conn.update_secret(
            SecretId="test-secret", SecretString="barsecret"
        )

    assert_equal(
        "Secrets Manager can't find the specified secret.",
        cm.exception.response["Error"]["Message"],
    )


@mock_secretsmanager
def test_update_secret_marked_as_deleted():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    created_secret = conn.create_secret(Name="test-secret", SecretString="foosecret")
    deleted_secret = conn.delete_secret(SecretId="test-secret")

    with assert_raises(ClientError) as cm:
        updated_secret = conn.update_secret(
            SecretId="test-secret", SecretString="barsecret"
        )

    assert (
        "because it was marked for deletion."
        in cm.exception.response["Error"]["Message"]
    )


@mock_secretsmanager
def test_update_secret_marked_as_deleted_after_restoring():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    created_secret = conn.create_secret(Name="test-secret", SecretString="foosecret")
    deleted_secret = conn.delete_secret(SecretId="test-secret")
    restored_secret = conn.restore_secret(SecretId="test-secret")

    updated_secret = conn.update_secret(
        SecretId="test-secret", SecretString="barsecret"
    )

    assert updated_secret["ARN"]
    assert updated_secret["Name"] == "test-secret"
    assert updated_secret["VersionId"] != ""
