# -*- coding: utf-8 -*-
import boto3

from moto import mock_secretsmanager
from botocore.exceptions import ClientError
import sure  # noqa # pylint: disable=unused-import
import pytest


def boto_client():
    return boto3.client("secretsmanager", region_name="us-west-2")


@mock_secretsmanager
def test_empty():
    conn = boto_client()

    secrets = conn.list_secrets()

    assert secrets["SecretList"] == []


@mock_secretsmanager
def test_list_secrets():
    conn = boto_client()

    conn.create_secret(Name="test-secret", SecretString="foosecret")

    conn.create_secret(
        Name="test-secret-2",
        SecretString="barsecret",
        Tags=[{"Key": "a", "Value": "1"}],
    )

    secrets = conn.list_secrets()

    assert secrets["SecretList"][0]["ARN"] is not None
    assert secrets["SecretList"][0]["Name"] == "test-secret"
    assert secrets["SecretList"][0]["SecretVersionsToStages"] is not None
    assert secrets["SecretList"][1]["ARN"] is not None
    assert secrets["SecretList"][1]["Name"] == "test-secret-2"
    assert secrets["SecretList"][1]["Tags"] == [{"Key": "a", "Value": "1"}]
    assert secrets["SecretList"][1]["SecretVersionsToStages"] is not None


@mock_secretsmanager
def test_with_name_filter():
    conn = boto_client()

    conn.create_secret(Name="foo", SecretString="secret")
    conn.create_secret(Name="bar", SecretString="secret")

    secrets = conn.list_secrets(Filters=[{"Key": "name", "Values": ["foo"]}])

    secret_names = list(map(lambda s: s["Name"], secrets["SecretList"]))
    assert secret_names == ["foo"]


@mock_secretsmanager
def test_with_tag_key_filter():
    conn = boto_client()

    conn.create_secret(
        Name="foo", SecretString="secret", Tags=[{"Key": "baz", "Value": "1"}]
    )
    conn.create_secret(Name="bar", SecretString="secret")

    secrets = conn.list_secrets(Filters=[{"Key": "tag-key", "Values": ["baz"]}])

    secret_names = list(map(lambda s: s["Name"], secrets["SecretList"]))
    assert secret_names == ["foo"]


@mock_secretsmanager
def test_with_tag_value_filter():
    conn = boto_client()

    conn.create_secret(
        Name="foo", SecretString="secret", Tags=[{"Key": "1", "Value": "baz"}]
    )
    conn.create_secret(Name="bar", SecretString="secret")

    secrets = conn.list_secrets(Filters=[{"Key": "tag-value", "Values": ["baz"]}])

    secret_names = list(map(lambda s: s["Name"], secrets["SecretList"]))
    assert secret_names == ["foo"]


@mock_secretsmanager
def test_with_description_filter():
    conn = boto_client()

    conn.create_secret(Name="foo", SecretString="secret", Description="baz qux")
    conn.create_secret(Name="bar", SecretString="secret")

    secrets = conn.list_secrets(Filters=[{"Key": "description", "Values": ["baz"]}])

    secret_names = list(map(lambda s: s["Name"], secrets["SecretList"]))
    assert secret_names == ["foo"]


@mock_secretsmanager
def test_with_all_filter():
    # The 'all' filter will match a secret that contains ANY field with the criteria. In other words an implicit OR.

    conn = boto_client()

    conn.create_secret(Name="foo", SecretString="secret")
    conn.create_secret(Name="bar", SecretString="secret", Description="foo")
    conn.create_secret(
        Name="baz", SecretString="secret", Tags=[{"Key": "foo", "Value": "1"}]
    )
    conn.create_secret(
        Name="qux", SecretString="secret", Tags=[{"Key": "1", "Value": "foo"}]
    )
    conn.create_secret(
        Name="multi", SecretString="secret", Tags=[{"Key": "foo", "Value": "foo"}]
    )
    conn.create_secret(Name="none", SecretString="secret")

    secrets = conn.list_secrets(Filters=[{"Key": "all", "Values": ["foo"]}])

    secret_names = list(map(lambda s: s["Name"], secrets["SecretList"]))
    assert sorted(secret_names) == ["bar", "baz", "foo", "multi", "qux"]


@mock_secretsmanager
def test_with_no_filter_key():
    conn = boto_client()

    with pytest.raises(ClientError) as ire:
        conn.list_secrets(Filters=[{"Values": ["foo"]}])

    ire.value.response["Error"]["Code"].should.equal("InvalidParameterException")
    ire.value.response["Error"]["Message"].should.equal("Invalid filter key")


@mock_secretsmanager
def test_with_no_filter_values():
    conn = boto_client()

    conn.create_secret(Name="foo", SecretString="secret", Description="hello")

    with pytest.raises(ClientError) as ire:
        conn.list_secrets(Filters=[{"Key": "description"}])

    ire.value.response["Error"]["Code"].should.equal("InvalidParameterException")
    ire.value.response["Error"]["Message"].should.equal(
        "Invalid filter values for key: description"
    )


@mock_secretsmanager
def test_with_invalid_filter_key():
    conn = boto_client()

    with pytest.raises(ClientError) as ire:
        conn.list_secrets(Filters=[{"Key": "invalid", "Values": ["foo"]}])

    ire.value.response["Error"]["Code"].should.equal("ValidationException")
    ire.value.response["Error"]["Message"].should.equal(
        "1 validation error detected: Value 'invalid' at 'filters.1.member.key' failed to satisfy constraint: Member "
        "must satisfy enum value set: [all, name, tag-key, description, tag-value]"
    )


@mock_secretsmanager
def test_with_duplicate_filter_keys():
    # Multiple filters with the same key combine with an implicit AND operator

    conn = boto_client()

    conn.create_secret(Name="foo", SecretString="secret", Description="one two")
    conn.create_secret(Name="bar", SecretString="secret", Description="one")
    conn.create_secret(Name="baz", SecretString="secret", Description="two")
    conn.create_secret(Name="qux", SecretString="secret", Description="unrelated")

    secrets = conn.list_secrets(
        Filters=[
            {"Key": "description", "Values": ["one"]},
            {"Key": "description", "Values": ["two"]},
        ]
    )

    secret_names = list(map(lambda s: s["Name"], secrets["SecretList"]))
    assert secret_names == ["foo"]


@mock_secretsmanager
def test_with_multiple_filters():
    # Multiple filters combine with an implicit AND operator

    conn = boto_client()

    conn.create_secret(
        Name="foo", SecretString="secret", Tags=[{"Key": "right", "Value": "right"}]
    )
    conn.create_secret(
        Name="bar", SecretString="secret", Tags=[{"Key": "right", "Value": "wrong"}]
    )
    conn.create_secret(
        Name="baz", SecretString="secret", Tags=[{"Key": "wrong", "Value": "right"}]
    )
    conn.create_secret(
        Name="qux", SecretString="secret", Tags=[{"Key": "wrong", "Value": "wrong"}]
    )

    secrets = conn.list_secrets(
        Filters=[
            {"Key": "tag-key", "Values": ["right"]},
            {"Key": "tag-value", "Values": ["right"]},
        ]
    )

    secret_names = list(map(lambda s: s["Name"], secrets["SecretList"]))
    assert secret_names == ["foo"]


@mock_secretsmanager
def test_with_filter_with_multiple_values():
    conn = boto_client()

    conn.create_secret(Name="foo", SecretString="secret")
    conn.create_secret(Name="bar", SecretString="secret")
    conn.create_secret(Name="baz", SecretString="secret")

    secrets = conn.list_secrets(Filters=[{"Key": "name", "Values": ["foo", "bar"]}])

    secret_names = list(map(lambda s: s["Name"], secrets["SecretList"]))
    assert secret_names == ["foo", "bar"]


@mock_secretsmanager
def test_with_filter_with_value_with_multiple_words():
    conn = boto_client()

    conn.create_secret(Name="foo", SecretString="secret", Description="one two")
    conn.create_secret(Name="bar", SecretString="secret", Description="one and two")
    conn.create_secret(Name="baz", SecretString="secret", Description="one")
    conn.create_secret(Name="qux", SecretString="secret", Description="two")
    conn.create_secret(Name="none", SecretString="secret", Description="unrelated")

    secrets = conn.list_secrets(Filters=[{"Key": "description", "Values": ["one two"]}])

    secret_names = list(map(lambda s: s["Name"], secrets["SecretList"]))
    assert secret_names == ["foo", "bar"]


@mock_secretsmanager
def test_with_filter_with_negation():
    conn = boto_client()

    conn.create_secret(Name="foo", SecretString="secret", Description="one two")
    conn.create_secret(Name="bar", SecretString="secret", Description="one and two")
    conn.create_secret(Name="baz", SecretString="secret", Description="one")
    conn.create_secret(Name="qux", SecretString="secret", Description="two")
    conn.create_secret(Name="none", SecretString="secret", Description="unrelated")

    secrets = conn.list_secrets(
        Filters=[{"Key": "description", "Values": ["one", "!two"]}]
    )

    secret_names = list(map(lambda s: s["Name"], secrets["SecretList"]))
    assert secret_names == ["baz"]
