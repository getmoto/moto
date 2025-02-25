from datetime import datetime
from uuid import uuid4

import boto3
import pytest
from botocore.exceptions import ClientError
from dateutil.tz import tzlocal

from moto import mock_aws
from moto.secretsmanager.list_secrets.filters import split_words
from tests import aws_verified


def boto_client():
    return boto3.client("secretsmanager", region_name="us-west-2")


@mock_aws
def test_empty():
    conn = boto_client()

    secrets = conn.list_secrets()

    assert secrets["SecretList"] == []


@mock_aws
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
    assert secrets["SecretList"][0]["CreatedDate"] <= datetime.now(tz=tzlocal())
    assert secrets["SecretList"][1]["CreatedDate"] <= datetime.now(tz=tzlocal())
    assert secrets["SecretList"][0]["LastChangedDate"] <= datetime.now(tz=tzlocal())
    assert secrets["SecretList"][1]["LastChangedDate"] <= datetime.now(tz=tzlocal())


@mock_aws
def test_with_name_filter():
    conn = boto_client()

    conn.create_secret(Name="foo", SecretString="secret")
    conn.create_secret(Name="bar", SecretString="secret")

    secrets = conn.list_secrets(Filters=[{"Key": "name", "Values": ["foo"]}])

    secret_names = list(map(lambda s: s["Name"], secrets["SecretList"]))
    assert secret_names == ["foo"]


@mock_aws
def test_with_tag_key_filter():
    conn = boto_client()

    conn.create_secret(
        Name="foo", SecretString="secret", Tags=[{"Key": "baz", "Value": "1"}]
    )
    conn.create_secret(Name="bar", SecretString="secret")

    secrets = conn.list_secrets(Filters=[{"Key": "tag-key", "Values": ["baz"]}])

    secret_names = list(map(lambda s: s["Name"], secrets["SecretList"]))
    assert secret_names == ["foo"]


@mock_aws
def test_with_tag_value_filter():
    conn = boto_client()

    conn.create_secret(
        Name="foo", SecretString="secret", Tags=[{"Key": "1", "Value": "baz"}]
    )
    conn.create_secret(Name="bar", SecretString="secret")

    secrets = conn.list_secrets(Filters=[{"Key": "tag-value", "Values": ["baz"]}])

    secret_names = list(map(lambda s: s["Name"], secrets["SecretList"]))
    assert secret_names == ["foo"]


@mock_aws
def test_with_description_filter():
    conn = boto_client()

    conn.create_secret(Name="foo", SecretString="secret", Description="baz qux")
    conn.create_secret(Name="bar", SecretString="secret")

    secrets = conn.list_secrets(Filters=[{"Key": "description", "Values": ["baz"]}])

    secret_names = list(map(lambda s: s["Name"], secrets["SecretList"]))
    assert secret_names == ["foo"]


@aws_verified
# Verified, but not marked because it's flaky - AWS can take up to 5 minutes before secrets are listed
def test_with_all_filter():
    # The 'all' filter will match a secret that contains ANY field with
    # the criteria. In other words an implicit OR.
    unique_name = str(uuid4())[0:6]

    first_secret = f"SecretOne{unique_name}"
    second_secret = f"SecretTwo{unique_name}"
    third_secret = f"Thirdsecret{unique_name}"
    foo_tag_key = f"SecretFTag{unique_name}"
    foo_tag_val = f"SecretFValue{unique_name}"
    no_match = f"none{unique_name}"

    conn = boto_client()

    conn.create_secret(Name=first_secret, SecretString="s")
    conn.create_secret(Name=second_secret, SecretString="s", Description="DescTwo")
    conn.create_secret(Name=third_secret, SecretString="s")
    conn.create_secret(
        Name=foo_tag_key, SecretString="s", Tags=[{"Key": "1", "Value": "foo"}]
    )
    conn.create_secret(
        Name=foo_tag_val, SecretString="s", Tags=[{"Key": "foo", "Value": "v"}]
    )
    conn.create_secret(Name=no_match, SecretString="s")

    try:
        # Full Match
        secrets = conn.list_secrets(Filters=[{"Key": "all", "Values": ["SecretOne"]}])[
            "SecretList"
        ]
        secret_names = [s["Name"] for s in secrets]
        assert secret_names == [first_secret]

        # Search in tags
        secrets = conn.list_secrets(Filters=[{"Key": "all", "Values": ["foo"]}])[
            "SecretList"
        ]
        secret_names = [s["Name"] for s in secrets]
        assert secret_names == [foo_tag_key, foo_tag_val]

        # StartsWith - full word
        secrets = conn.list_secrets(Filters=[{"Key": "all", "Values": ["Secret"]}])[
            "SecretList"
        ]
        secret_names = [s["Name"] for s in secrets]
        assert secret_names == [first_secret, second_secret, foo_tag_key, foo_tag_val]

        # Partial Match - full word - lowercase
        secrets = conn.list_secrets(Filters=[{"Key": "all", "Values": ["secret"]}])[
            "SecretList"
        ]
        secret_names = [s["Name"] for s in secrets]
        assert secret_names == [first_secret, second_secret, foo_tag_key, foo_tag_val]

        # Partial Match - partial word
        secrets = conn.list_secrets(Filters=[{"Key": "all", "Values": ["ret"]}])[
            "SecretList"
        ]
        secret_names = [s["Name"] for s in secrets]
        assert not secret_names

        # Partial Match - partial word
        secrets = conn.list_secrets(Filters=[{"Key": "all", "Values": ["sec"]}])[
            "SecretList"
        ]
        secret_names = [s["Name"] for s in secrets]
        assert secret_names == [first_secret, second_secret, foo_tag_key, foo_tag_val]

        # Unknown Match
        secrets = conn.list_secrets(Filters=[{"Key": "all", "Values": ["SomeSecret"]}])[
            "SecretList"
        ]
        assert not secrets

        # Single value
        # Only matches description that contains a d
        secrets = conn.list_secrets(Filters=[{"Key": "all", "Values": ["d"]}])[
            "SecretList"
        ]
        secret_names = [s["Name"] for s in secrets]
        assert secret_names == [second_secret]

        # Multiple values
        # Only matches description that contains a d and t (DescTwo)
        secrets = conn.list_secrets(Filters=[{"Key": "all", "Values": ["d t"]}])[
            "SecretList"
        ]
        secret_names = [s["Name"] for s in secrets]
        assert secret_names == [second_secret]

        # Name parts that start with a t (DescTwo)
        secrets = conn.list_secrets(Filters=[{"Key": "all", "Values": ["t"]}])[
            "SecretList"
        ]
        secret_names = [s["Name"] for s in secrets]
        assert secret_names == [second_secret, third_secret, foo_tag_key]
    finally:
        conn.delete_secret(SecretId=first_secret, ForceDeleteWithoutRecovery=True)
        conn.delete_secret(SecretId=second_secret, ForceDeleteWithoutRecovery=True)
        conn.delete_secret(SecretId=third_secret, ForceDeleteWithoutRecovery=True)
        conn.delete_secret(SecretId=foo_tag_key, ForceDeleteWithoutRecovery=True)
        conn.delete_secret(SecretId=foo_tag_val, ForceDeleteWithoutRecovery=True)
        conn.delete_secret(SecretId=no_match, ForceDeleteWithoutRecovery=True)


@aws_verified
# Verified, but not marked because it's flaky - AWS can take up to 5 minutes before secrets are listed
def test_with_all_filter_special_characters():
    unique_name = str(uuid4())[0:6]
    secret_with_slash = f"prod/AppBeta/{unique_name}"
    secret_with_under = f"prod_AppBeta_{unique_name}"
    secret_with_plus = f"prod+AppBeta+{unique_name}"
    secret_with_equal = f"prod=AppBeta={unique_name}"
    secret_with_dot = f"prod.AppBeta.{unique_name}"
    secret_with_at = f"prod@AppBeta@{unique_name}"
    secret_with_dash = f"prod-AppBeta-{unique_name}"
    # Note that this secret is never found, because the pattern is unknown
    secret_with_dash_and_slash = f"prod-AppBeta/{unique_name}"
    full_uppercase = f"uat/COMPANY/{unique_name}"
    partial_uppercase = f"uat/COMPANYthings/{unique_name}"

    all_special_char_names = [
        secret_with_slash,
        secret_with_under,
        secret_with_plus,
        secret_with_equal,
        secret_with_dot,
        secret_with_at,
        secret_with_dash,
    ]

    conn = boto_client()

    conn.create_secret(Name=secret_with_slash, SecretString="s")
    conn.create_secret(Name=secret_with_under, SecretString="s")
    conn.create_secret(Name=secret_with_plus, SecretString="s")
    conn.create_secret(Name=secret_with_equal, SecretString="s")
    conn.create_secret(Name=secret_with_dot, SecretString="s")
    conn.create_secret(Name=secret_with_at, SecretString="s")
    conn.create_secret(Name=secret_with_dash, SecretString="s")
    conn.create_secret(Name=full_uppercase, SecretString="s")
    conn.create_secret(Name=partial_uppercase, SecretString="s")

    try:
        # Partial Match
        secrets = conn.list_secrets(Filters=[{"Key": "all", "Values": ["AppBeta"]}])
        secret_names = [s["Name"] for s in secrets["SecretList"]]
        assert secret_names == all_special_char_names

        # Partial Match
        secrets = conn.list_secrets(Filters=[{"Key": "all", "Values": ["Beta"]}])
        secret_names = [s["Name"] for s in secrets["SecretList"]]
        assert secret_names == all_special_char_names

        secrets = conn.list_secrets(
            Filters=[{"Key": "all", "Values": ["AppBeta", "prod"]}]
        )["SecretList"]
        secret_names = [s["Name"] for s in secrets]
        assert secret_names == all_special_char_names

        # Search for special character itself
        secrets = conn.list_secrets(Filters=[{"Key": "all", "Values": ["+"]}])
        secret_names = [s["Name"] for s in secrets["SecretList"]]
        assert not secret_names

        # Search for unique postfix
        secrets = conn.list_secrets(Filters=[{"Key": "all", "Values": [unique_name]}])
        secret_names = [s["Name"] for s in secrets["SecretList"]]
        assert secret_names == (
            all_special_char_names + [full_uppercase, partial_uppercase]
        )

        # Search for unique postfix
        secrets = conn.list_secrets(Filters=[{"Key": "all", "Values": ["company"]}])
        secret_names = [s["Name"] for s in secrets["SecretList"]]
        assert secret_names == [full_uppercase]

        # This on it's own is not a word
        secrets = conn.list_secrets(Filters=[{"Key": "all", "Values": ["things"]}])
        secret_names = [s["Name"] for s in secrets["SecretList"]]
        assert secret_names == []

        # This is valid, because it's split as COMPAN + Ythings
        secrets = conn.list_secrets(Filters=[{"Key": "all", "Values": ["Ythings"]}])
        secret_names = [s["Name"] for s in secrets["SecretList"]]
        assert secret_names == [partial_uppercase]

        # Note that individual letters from COMPANY are not searchable,
        # indicating that AWS splits by terms, rather than each individual upper case
        # COMPANYThings --> COMPAN, YThings
        secrets = conn.list_secrets(Filters=[{"Key": "all", "Values": ["N"]}])
        secret_names = [s["Name"] for s in secrets["SecretList"]]
        assert secret_names == []

        #
        secrets = conn.list_secrets(Filters=[{"Key": "all", "Values": ["pany"]}])
        secret_names = [s["Name"] for s in secrets["SecretList"]]
        assert secret_names == []

    finally:
        conn.delete_secret(SecretId=secret_with_slash, ForceDeleteWithoutRecovery=True)
        conn.delete_secret(SecretId=secret_with_under, ForceDeleteWithoutRecovery=True)
        conn.delete_secret(SecretId=secret_with_plus, ForceDeleteWithoutRecovery=True)
        conn.delete_secret(SecretId=secret_with_equal, ForceDeleteWithoutRecovery=True)
        conn.delete_secret(SecretId=secret_with_dot, ForceDeleteWithoutRecovery=True)
        conn.delete_secret(SecretId=secret_with_dash, ForceDeleteWithoutRecovery=True)
        conn.delete_secret(
            SecretId=secret_with_dash_and_slash, ForceDeleteWithoutRecovery=True
        )
        conn.delete_secret(SecretId=secret_with_at, ForceDeleteWithoutRecovery=True)
        conn.delete_secret(SecretId=full_uppercase, ForceDeleteWithoutRecovery=True)
        conn.delete_secret(SecretId=partial_uppercase, ForceDeleteWithoutRecovery=True)


@mock_aws
def test_with_no_filter_key():
    conn = boto_client()

    with pytest.raises(ClientError) as ire:
        conn.list_secrets(Filters=[{"Values": ["foo"]}])

    assert ire.value.response["Error"]["Code"] == "InvalidParameterException"
    assert ire.value.response["Error"]["Message"] == "Invalid filter key"


@mock_aws
def test_with_no_filter_values():
    conn = boto_client()

    conn.create_secret(Name="foo", SecretString="secret", Description="hello")

    with pytest.raises(ClientError) as ire:
        conn.list_secrets(Filters=[{"Key": "description"}])

    assert ire.value.response["Error"]["Code"] == "InvalidParameterException"
    assert ire.value.response["Error"]["Message"] == (
        "Invalid filter values for key: description"
    )


@mock_aws
def test_with_invalid_filter_key():
    conn = boto_client()

    with pytest.raises(ClientError) as ire:
        conn.list_secrets(Filters=[{"Key": "invalid", "Values": ["foo"]}])

    assert ire.value.response["Error"]["Code"] == "ValidationException"
    assert ire.value.response["Error"]["Message"] == (
        "1 validation error detected: Value 'invalid' at "
        "'filters.1.member.key' failed to satisfy constraint: Member "
        "must satisfy enum value set: [all, name, tag-key, description, tag-value]"
    )


@aws_verified
# Verified, but not marked because it's flaky - AWS can take up to 5 minutes before secrets are listed
def test_with_duplicate_filter_keys():
    # Multiple filters with the same key combine with an implicit AND operator

    conn = boto_client()

    conn.create_secret(Name="foo", SecretString="secret", Description="one two")
    conn.create_secret(Name="bar", SecretString="secret", Description="one")
    conn.create_secret(Name="baz", SecretString="secret", Description="two")
    conn.create_secret(Name="qux", SecretString="secret", Description="unrelated")

    try:
        secrets = conn.list_secrets(
            Filters=[
                {"Key": "description", "Values": ["one"]},
                {"Key": "description", "Values": ["two"]},
            ]
        )

        secret_names = list(map(lambda s: s["Name"], secrets["SecretList"]))
        assert secret_names == ["foo"]
    finally:
        conn.delete_secret(SecretId="foo", ForceDeleteWithoutRecovery=True)
        conn.delete_secret(SecretId="bar", ForceDeleteWithoutRecovery=True)
        conn.delete_secret(SecretId="baz", ForceDeleteWithoutRecovery=True)
        conn.delete_secret(SecretId="qux", ForceDeleteWithoutRecovery=True)


@mock_aws
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


@mock_aws
def test_with_filter_with_multiple_values():
    conn = boto_client()

    conn.create_secret(Name="foo", SecretString="secret")
    conn.create_secret(Name="bar", SecretString="secret")
    conn.create_secret(Name="baz", SecretString="secret")

    secrets = conn.list_secrets(Filters=[{"Key": "name", "Values": ["foo", "bar"]}])

    secret_names = list(map(lambda s: s["Name"], secrets["SecretList"]))
    assert secret_names == ["foo", "bar"]


@aws_verified
# Verified, but not marked because it's flaky - AWS can take up to 5 minutes before secrets are listed
def test_with_filter_with_value_with_multiple_words():
    conn = boto_client()

    conn.create_secret(Name="foo", SecretString="secret", Description="one two")
    conn.create_secret(Name="bar", SecretString="secret", Description="one and two")
    conn.create_secret(Name="baz", SecretString="secret", Description="one")
    conn.create_secret(Name="qux", SecretString="secret", Description="two")
    conn.create_secret(Name="none", SecretString="secret", Description="unrelated")

    try:
        # All values that contain one and two
        secrets = conn.list_secrets(
            Filters=[{"Key": "description", "Values": ["one two"]}]
        )
        secret_names = list(map(lambda s: s["Name"], secrets["SecretList"]))
        assert secret_names == ["foo", "bar"]

        # All values that start with o and t
        secrets = conn.list_secrets(Filters=[{"Key": "description", "Values": ["o t"]}])
        secret_names = list(map(lambda s: s["Name"], secrets["SecretList"]))
        assert secret_names == ["foo", "bar"]

        # All values that contain t
        secrets = conn.list_secrets(Filters=[{"Key": "description", "Values": ["t"]}])
        secret_names = list(map(lambda s: s["Name"], secrets["SecretList"]))
        assert secret_names == ["foo", "bar", "qux"]
    finally:
        conn.delete_secret(SecretId="foo", ForceDeleteWithoutRecovery=True)
        conn.delete_secret(SecretId="bar", ForceDeleteWithoutRecovery=True)
        conn.delete_secret(SecretId="baz", ForceDeleteWithoutRecovery=True)
        conn.delete_secret(SecretId="qux", ForceDeleteWithoutRecovery=True)
        conn.delete_secret(SecretId="none", ForceDeleteWithoutRecovery=True)


@mock_aws
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
    for secret_name in ["foo", "bar", "baz"]:
        assert secret_name in secret_names

    secrets = conn.list_secrets(Filters=[{"Key": "description", "Values": ["!o"]}])
    secret_names = list(map(lambda s: s["Name"], secrets["SecretList"]))
    for secret_name in ["qux", "none"]:
        assert secret_name in secret_names


@mock_aws
def test_filter_with_owning_service():
    conn = boto3.client("secretsmanager", region_name="us-west-2")

    conn.create_secret(Name="foo", SecretString="secret")

    resp = conn.list_secrets(Filters=[{"Key": "owning-service", "Values": ["n/a"]}])
    assert resp["SecretList"] == []


@mock_aws
def test_with_include_planned_deleted_secrets():
    conn = boto_client()

    conn.create_secret(Name="foo", SecretString="secret")
    conn.create_secret(Name="bar", SecretString="secret")

    secrets = conn.list_secrets()
    assert len(secrets["SecretList"]) == 2

    conn.delete_secret(SecretId="foo")

    # By default list secrets doesn't include deleted secrets
    secrets = conn.list_secrets()
    assert len(secrets["SecretList"]) == 1
    assert secrets["SecretList"][0]["ARN"] is not None
    assert secrets["SecretList"][0]["Name"] == "bar"
    assert secrets["SecretList"][0]["SecretVersionsToStages"] is not None

    # list secrets when IncludePlannedDeletion param included
    secrets = conn.list_secrets(IncludePlannedDeletion=True)
    assert len(secrets["SecretList"]) == 2

    # list secret with filter and IncludePlannedDeletion params
    secrets = conn.list_secrets(
        IncludePlannedDeletion=True, Filters=[{"Key": "name", "Values": ["foo"]}]
    )
    assert len(secrets["SecretList"]) == 1
    assert secrets["SecretList"][0]["ARN"] is not None
    assert secrets["SecretList"][0]["Name"] == "foo"
    assert secrets["SecretList"][0]["SecretVersionsToStages"] is not None


@pytest.mark.parametrize(
    "input,output",
    [
        ("test", ["test"]),
        ("my test", ["my", "test"]),
        ("Mytest", ["Mytest"]),
        ("MyTest", ["My", "Test"]),
        ("MyTestPhrase", ["My", "Test", "Phrase"]),
        ("myTest", ["my", "Test"]),
        ("my test", ["my", "test"]),
        ("my/test", ["my", "test"]),
    ],
)
def test_word_splitter(input, output):
    assert split_words(input) == output
