# -*- coding: utf-8 -*-
import base64
import re

import boto.kms
import boto3
import sure  # noqa # pylint: disable=unused-import
from boto.exception import JSONResponseError
from boto.kms.exceptions import AlreadyExistsException, NotFoundException
import pytest
from moto.core.exceptions import JsonRESTError
from moto.kms.models import KmsBackend
from moto.kms.exceptions import NotFoundException as MotoNotFoundException
from moto import mock_kms_deprecated, mock_kms

PLAINTEXT_VECTORS = [
    b"some encodeable plaintext",
    b"some unencodeable plaintext \xec\x8a\xcf\xb6r\xe9\xb5\xeb\xff\xa23\x16",
    "some unicode characters ø˚∆øˆˆ∆ßçøˆˆçßøˆ¨¥",
]


def _get_encoded_value(plaintext):
    if isinstance(plaintext, bytes):
        return plaintext

    return plaintext.encode("utf-8")


# Has boto3 equivalent
@mock_kms_deprecated
def test_describe_key():
    conn = boto.kms.connect_to_region("us-west-2")
    key = conn.create_key(
        policy="my policy", description="my key", key_usage="ENCRYPT_DECRYPT"
    )
    key_id = key["KeyMetadata"]["KeyId"]

    key = conn.describe_key(key_id)
    key["KeyMetadata"]["Description"].should.equal("my key")
    key["KeyMetadata"]["KeyUsage"].should.equal("ENCRYPT_DECRYPT")


# Has boto3 equivalent
@mock_kms_deprecated
def test_describe_key_via_alias():
    conn = boto.kms.connect_to_region("us-west-2")
    key = conn.create_key(
        policy="my policy", description="my key", key_usage="ENCRYPT_DECRYPT"
    )
    conn.create_alias(
        alias_name="alias/my-key-alias", target_key_id=key["KeyMetadata"]["KeyId"]
    )

    alias_key = conn.describe_key("alias/my-key-alias")
    alias_key["KeyMetadata"]["Description"].should.equal("my key")
    alias_key["KeyMetadata"]["KeyUsage"].should.equal("ENCRYPT_DECRYPT")
    alias_key["KeyMetadata"]["Arn"].should.equal(key["KeyMetadata"]["Arn"])


# Has boto3 equivalent
@mock_kms_deprecated
def test_describe_key_via_alias_not_found():
    conn = boto.kms.connect_to_region("us-west-2")
    key = conn.create_key(
        policy="my policy", description="my key", key_usage="ENCRYPT_DECRYPT"
    )
    conn.create_alias(
        alias_name="alias/my-key-alias", target_key_id=key["KeyMetadata"]["KeyId"]
    )

    conn.describe_key.when.called_with("alias/not-found-alias").should.throw(
        NotFoundException
    )


# Has boto3 equivalent
@mock_kms_deprecated
def test_describe_key_via_arn():
    conn = boto.kms.connect_to_region("us-west-2")
    key = conn.create_key(
        policy="my policy", description="my key", key_usage="ENCRYPT_DECRYPT"
    )
    arn = key["KeyMetadata"]["Arn"]

    the_key = conn.describe_key(arn)
    the_key["KeyMetadata"]["Description"].should.equal("my key")
    the_key["KeyMetadata"]["KeyUsage"].should.equal("ENCRYPT_DECRYPT")
    the_key["KeyMetadata"]["KeyId"].should.equal(key["KeyMetadata"]["KeyId"])


# Has boto3 equivalent
@mock_kms_deprecated
def test_describe_missing_key():
    conn = boto.kms.connect_to_region("us-west-2")
    conn.describe_key.when.called_with("not-a-key").should.throw(NotFoundException)


# Has boto3 equivalent
@mock_kms_deprecated
def test_list_keys():
    conn = boto.kms.connect_to_region("us-west-2")

    conn.create_key(
        policy="my policy", description="my key1", key_usage="ENCRYPT_DECRYPT"
    )
    conn.create_key(
        policy="my policy", description="my key2", key_usage="ENCRYPT_DECRYPT"
    )

    keys = conn.list_keys()
    keys["Keys"].should.have.length_of(2)


# Has boto3 equivalent
@mock_kms_deprecated
def test_enable_key_rotation():
    conn = boto.kms.connect_to_region("us-west-2")

    key = conn.create_key(
        policy="my policy", description="my key", key_usage="ENCRYPT_DECRYPT"
    )
    key_id = key["KeyMetadata"]["KeyId"]

    conn.enable_key_rotation(key_id)

    conn.get_key_rotation_status(key_id)["KeyRotationEnabled"].should.equal(True)


# Has boto3 equivalent
@mock_kms_deprecated
def test_enable_key_rotation_via_arn():
    conn = boto.kms.connect_to_region("us-west-2")

    key = conn.create_key(
        policy="my policy", description="my key", key_usage="ENCRYPT_DECRYPT"
    )
    key_id = key["KeyMetadata"]["Arn"]

    conn.enable_key_rotation(key_id)

    conn.get_key_rotation_status(key_id)["KeyRotationEnabled"].should.equal(True)


# Has boto3 equivalent
@mock_kms_deprecated
def test_enable_key_rotation_with_missing_key():
    conn = boto.kms.connect_to_region("us-west-2")
    conn.enable_key_rotation.when.called_with("not-a-key").should.throw(
        NotFoundException
    )


# Has boto3 equivalent
@mock_kms_deprecated
def test_enable_key_rotation_with_alias_name_should_fail():
    conn = boto.kms.connect_to_region("us-west-2")
    key = conn.create_key(
        policy="my policy", description="my key", key_usage="ENCRYPT_DECRYPT"
    )
    conn.create_alias(
        alias_name="alias/my-key-alias", target_key_id=key["KeyMetadata"]["KeyId"]
    )

    alias_key = conn.describe_key("alias/my-key-alias")
    alias_key["KeyMetadata"]["Arn"].should.equal(key["KeyMetadata"]["Arn"])

    conn.enable_key_rotation.when.called_with("alias/my-alias").should.throw(
        NotFoundException
    )


# Has boto3 equivalent
@mock_kms_deprecated
def test_disable_key_rotation():
    conn = boto.kms.connect_to_region("us-west-2")

    key = conn.create_key(
        policy="my policy", description="my key", key_usage="ENCRYPT_DECRYPT"
    )
    key_id = key["KeyMetadata"]["KeyId"]

    conn.enable_key_rotation(key_id)
    conn.get_key_rotation_status(key_id)["KeyRotationEnabled"].should.equal(True)

    conn.disable_key_rotation(key_id)
    conn.get_key_rotation_status(key_id)["KeyRotationEnabled"].should.equal(False)


# Has boto3 equivalent
@mock_kms_deprecated
def test_generate_data_key():
    conn = boto.kms.connect_to_region("us-west-2")

    key = conn.create_key(
        policy="my policy", description="my key", key_usage="ENCRYPT_DECRYPT"
    )
    key_id = key["KeyMetadata"]["KeyId"]
    key_arn = key["KeyMetadata"]["Arn"]

    response = conn.generate_data_key(key_id=key_id, number_of_bytes=32)

    # CiphertextBlob must NOT be base64-encoded
    with pytest.raises(Exception):
        base64.b64decode(response["CiphertextBlob"], validate=True)
    # Plaintext must NOT be base64-encoded
    with pytest.raises(Exception):
        base64.b64decode(response["Plaintext"], validate=True)

    response["KeyId"].should.equal(key_arn)


# Has boto3 equivalent
@mock_kms_deprecated
def test_disable_key_rotation_with_missing_key():
    conn = boto.kms.connect_to_region("us-west-2")
    conn.disable_key_rotation.when.called_with("not-a-key").should.throw(
        NotFoundException
    )


# Has boto3 equivalent
@mock_kms_deprecated
def test_get_key_rotation_status_with_missing_key():
    conn = boto.kms.connect_to_region("us-west-2")
    conn.get_key_rotation_status.when.called_with("not-a-key").should.throw(
        NotFoundException
    )


# Has boto3 equivalent
@mock_kms_deprecated
def test_get_key_rotation_status():
    conn = boto.kms.connect_to_region("us-west-2")

    key = conn.create_key(
        policy="my policy", description="my key", key_usage="ENCRYPT_DECRYPT"
    )
    key_id = key["KeyMetadata"]["KeyId"]

    conn.get_key_rotation_status(key_id)["KeyRotationEnabled"].should.equal(False)


# Has boto3 equivalent
@mock_kms_deprecated
def test_create_key_defaults_key_rotation():
    conn = boto.kms.connect_to_region("us-west-2")

    key = conn.create_key(
        policy="my policy", description="my key", key_usage="ENCRYPT_DECRYPT"
    )
    key_id = key["KeyMetadata"]["KeyId"]

    conn.get_key_rotation_status(key_id)["KeyRotationEnabled"].should.equal(False)


# Has boto3 equivalent
@mock_kms_deprecated
def test_get_key_policy():
    conn = boto.kms.connect_to_region("us-west-2")

    key = conn.create_key(
        policy="my policy", description="my key1", key_usage="ENCRYPT_DECRYPT"
    )
    key_id = key["KeyMetadata"]["KeyId"]

    policy = conn.get_key_policy(key_id, "default")
    policy["Policy"].should.equal("my policy")


# Has boto3 equivalent
@mock_kms_deprecated
def test_get_key_policy_via_arn():
    conn = boto.kms.connect_to_region("us-west-2")

    key = conn.create_key(
        policy="my policy", description="my key1", key_usage="ENCRYPT_DECRYPT"
    )
    policy = conn.get_key_policy(key["KeyMetadata"]["Arn"], "default")

    policy["Policy"].should.equal("my policy")


# Has boto3 equivalent
@mock_kms_deprecated
def test_put_key_policy():
    conn = boto.kms.connect_to_region("us-west-2")

    key = conn.create_key(
        policy="my policy", description="my key1", key_usage="ENCRYPT_DECRYPT"
    )
    key_id = key["KeyMetadata"]["KeyId"]

    conn.put_key_policy(key_id, "default", "new policy")
    policy = conn.get_key_policy(key_id, "default")
    policy["Policy"].should.equal("new policy")


# Has boto3 equivalent
@mock_kms_deprecated
def test_put_key_policy_via_arn():
    conn = boto.kms.connect_to_region("us-west-2")

    key = conn.create_key(
        policy="my policy", description="my key1", key_usage="ENCRYPT_DECRYPT"
    )
    key_id = key["KeyMetadata"]["Arn"]

    conn.put_key_policy(key_id, "default", "new policy")
    policy = conn.get_key_policy(key_id, "default")
    policy["Policy"].should.equal("new policy")


# Has boto3 equivalent
@mock_kms_deprecated
def test_put_key_policy_via_alias_should_not_update():
    conn = boto.kms.connect_to_region("us-west-2")

    key = conn.create_key(
        policy="my policy", description="my key1", key_usage="ENCRYPT_DECRYPT"
    )
    conn.create_alias(
        alias_name="alias/my-key-alias", target_key_id=key["KeyMetadata"]["KeyId"]
    )

    conn.put_key_policy.when.called_with(
        "alias/my-key-alias", "default", "new policy"
    ).should.throw(NotFoundException)

    policy = conn.get_key_policy(key["KeyMetadata"]["KeyId"], "default")
    policy["Policy"].should.equal("my policy")


# Has boto3 equivalent
@mock_kms_deprecated
def test_list_key_policies():
    conn = boto.kms.connect_to_region("us-west-2")

    key = conn.create_key(
        policy="my policy", description="my key1", key_usage="ENCRYPT_DECRYPT"
    )
    key_id = key["KeyMetadata"]["KeyId"]

    policies = conn.list_key_policies(key_id)
    policies["PolicyNames"].should.equal(["default"])


# Has boto3 equivalent
@mock_kms_deprecated
def test__create_alias__returns_none_if_correct():
    kms = boto.connect_kms()
    create_resp = kms.create_key()
    key_id = create_resp["KeyMetadata"]["KeyId"]

    resp = kms.create_alias("alias/my-alias", key_id)

    resp.should.be.none


# Has boto3 equivalent
@mock_kms_deprecated
def test__create_alias__raises_if_reserved_alias():
    kms = boto.connect_kms()
    create_resp = kms.create_key()
    key_id = create_resp["KeyMetadata"]["KeyId"]

    reserved_aliases = [
        "alias/aws/ebs",
        "alias/aws/s3",
        "alias/aws/redshift",
        "alias/aws/rds",
    ]

    for alias_name in reserved_aliases:
        with pytest.raises(JSONResponseError) as err:
            kms.create_alias(alias_name, key_id)

        ex = err.value
        ex.error_message.should.be.none
        ex.error_code.should.equal("NotAuthorizedException")
        ex.body.should.equal({"__type": "NotAuthorizedException"})
        ex.reason.should.equal("Bad Request")
        ex.status.should.equal(400)


# Has boto3 equivalent
@mock_kms_deprecated
def test__create_alias__can_create_multiple_aliases_for_same_key_id():
    kms = boto.connect_kms()
    create_resp = kms.create_key()
    key_id = create_resp["KeyMetadata"]["KeyId"]

    kms.create_alias("alias/my-alias3", key_id).should.be.none
    kms.create_alias("alias/my-alias4", key_id).should.be.none
    kms.create_alias("alias/my-alias5", key_id).should.be.none


# Has boto3 equivalent
@mock_kms_deprecated
def test__create_alias__raises_if_wrong_prefix():
    kms = boto.connect_kms()
    create_resp = kms.create_key()
    key_id = create_resp["KeyMetadata"]["KeyId"]

    with pytest.raises(JSONResponseError) as err:
        kms.create_alias("wrongprefix/my-alias", key_id)

    ex = err.value
    ex.error_message.should.equal("Invalid identifier")
    ex.error_code.should.equal("ValidationException")
    ex.body.should.equal(
        {"message": "Invalid identifier", "__type": "ValidationException"}
    )
    ex.reason.should.equal("Bad Request")
    ex.status.should.equal(400)


# Has boto3 equivalent
@mock_kms_deprecated
def test__create_alias__raises_if_duplicate():
    region = "us-west-2"
    kms = boto.kms.connect_to_region(region)
    create_resp = kms.create_key()
    key_id = create_resp["KeyMetadata"]["KeyId"]
    alias = "alias/my-alias"

    kms.create_alias(alias, key_id)

    with pytest.raises(AlreadyExistsException) as err:
        kms.create_alias(alias, key_id)

    ex = err.value
    ex.error_message.should.match(
        r"An alias with the name arn:aws:kms:{region}:\d{{12}}:{alias} already exists".format(
            **locals()
        )
    )
    ex.error_code.should.be.none
    ex.box_usage.should.be.none
    ex.request_id.should.be.none
    ex.body["message"].should.match(
        r"An alias with the name arn:aws:kms:{region}:\d{{12}}:{alias} already exists".format(
            **locals()
        )
    )
    ex.body["__type"].should.equal("AlreadyExistsException")
    ex.reason.should.equal("Bad Request")
    ex.status.should.equal(400)


# Has boto3 equivalent
@mock_kms_deprecated
def test__create_alias__raises_if_alias_has_restricted_characters():
    kms = boto.connect_kms()
    create_resp = kms.create_key()
    key_id = create_resp["KeyMetadata"]["KeyId"]

    alias_names_with_restricted_characters = [
        "alias/my-alias!",
        "alias/my-alias$",
        "alias/my-alias@",
    ]

    for alias_name in alias_names_with_restricted_characters:
        with pytest.raises(JSONResponseError) as err:
            kms.create_alias(alias_name, key_id)
        ex = err.value
        ex.body["__type"].should.equal("ValidationException")
        ex.body["message"].should.equal(
            "1 validation error detected: Value '{alias_name}' at 'aliasName' failed to satisfy constraint: Member must satisfy regular expression pattern: ^[a-zA-Z0-9:/_-]+$".format(
                **locals()
            )
        )
        ex.error_code.should.equal("ValidationException")
        ex.message.should.equal(
            "1 validation error detected: Value '{alias_name}' at 'aliasName' failed to satisfy constraint: Member must satisfy regular expression pattern: ^[a-zA-Z0-9:/_-]+$".format(
                **locals()
            )
        )
        ex.reason.should.equal("Bad Request")
        ex.status.should.equal(400)


# Has boto3 equivalent
@mock_kms_deprecated
def test__create_alias__raises_if_alias_has_colon_character():
    # For some reason, colons are not accepted for an alias, even though they
    # are accepted by regex ^[a-zA-Z0-9:/_-]+$
    kms = boto.connect_kms()
    create_resp = kms.create_key()
    key_id = create_resp["KeyMetadata"]["KeyId"]

    alias_names_with_restricted_characters = ["alias/my:alias"]

    for alias_name in alias_names_with_restricted_characters:
        with pytest.raises(JSONResponseError) as err:
            kms.create_alias(alias_name, key_id)
        ex = err.value
        ex.body["__type"].should.equal("ValidationException")
        ex.body["message"].should.equal(
            "{alias_name} contains invalid characters for an alias".format(**locals())
        )
        ex.error_code.should.equal("ValidationException")
        ex.message.should.equal(
            "{alias_name} contains invalid characters for an alias".format(**locals())
        )
        ex.reason.should.equal("Bad Request")
        ex.status.should.equal(400)


# Has boto3 equivalent
@pytest.mark.parametrize("alias_name", ["alias/my-alias_/", "alias/my_alias-/"])
@mock_kms_deprecated
def test__create_alias__accepted_characters(alias_name):
    kms = boto.connect_kms()
    create_resp = kms.create_key()
    key_id = create_resp["KeyMetadata"]["KeyId"]

    kms.create_alias(alias_name, key_id)


# Has boto3 equivalent
@mock_kms_deprecated
def test__create_alias__raises_if_target_key_id_is_existing_alias():
    kms = boto.connect_kms()
    create_resp = kms.create_key()
    key_id = create_resp["KeyMetadata"]["KeyId"]
    alias = "alias/my-alias"

    kms.create_alias(alias, key_id)

    with pytest.raises(JSONResponseError) as err:
        kms.create_alias(alias, alias)

    ex = err.value
    ex.body["__type"].should.equal("ValidationException")
    ex.body["message"].should.equal("Aliases must refer to keys. Not aliases")
    ex.error_code.should.equal("ValidationException")
    ex.message.should.equal("Aliases must refer to keys. Not aliases")
    ex.reason.should.equal("Bad Request")
    ex.status.should.equal(400)


# Has boto3 equivalent
@mock_kms_deprecated
def test__delete_alias():
    kms = boto.connect_kms()
    create_resp = kms.create_key()
    key_id = create_resp["KeyMetadata"]["KeyId"]
    alias = "alias/my-alias"

    # added another alias here to make sure that the deletion of the alias can
    # be done when there are multiple existing aliases.
    kms.create_key()
    another_key_id = create_resp["KeyMetadata"]["KeyId"]
    another_alias = "alias/another-alias"

    kms.create_alias(alias, key_id)
    kms.create_alias(another_alias, another_key_id)

    resp = kms.delete_alias(alias)

    resp.should.be.none

    # we can create the alias again, since it has been deleted
    kms.create_alias(alias, key_id)


# Has boto3 equivalent
@mock_kms_deprecated
def test__delete_alias__raises_if_wrong_prefix():
    kms = boto.connect_kms()

    with pytest.raises(JSONResponseError) as err:
        kms.delete_alias("wrongprefix/my-alias")

    ex = err.value
    ex.body["__type"].should.equal("ValidationException")
    ex.body["message"].should.equal("Invalid identifier")
    ex.error_code.should.equal("ValidationException")
    ex.message.should.equal("Invalid identifier")
    ex.reason.should.equal("Bad Request")
    ex.status.should.equal(400)


# Has boto3 equivalent
@mock_kms_deprecated
def test__delete_alias__raises_if_alias_is_not_found():
    region = "us-west-2"
    kms = boto.kms.connect_to_region(region)
    alias_name = "alias/unexisting-alias"

    with pytest.raises(NotFoundException) as err:
        kms.delete_alias(alias_name)

    expected_message_match = r"Alias arn:aws:kms:{region}:[0-9]{{12}}:{alias_name} is not found.".format(
        region=region, alias_name=alias_name
    )
    ex = err.value
    ex.body["__type"].should.equal("NotFoundException")
    ex.body["message"].should.match(expected_message_match)
    ex.box_usage.should.be.none
    ex.error_code.should.be.none
    ex.message.should.match(expected_message_match)
    ex.reason.should.equal("Bad Request")
    ex.request_id.should.be.none
    ex.status.should.equal(400)


# Has boto3 equivalent
@mock_kms_deprecated
def test__list_aliases():
    region = "eu-west-1"
    kms = boto.kms.connect_to_region(region)

    create_resp = kms.create_key()
    key_id = create_resp["KeyMetadata"]["KeyId"]
    kms.create_alias("alias/my-alias1", key_id)
    kms.create_alias("alias/my-alias2", key_id)
    kms.create_alias("alias/my-alias3", key_id)

    resp = kms.list_aliases()

    resp["Truncated"].should.be.false

    aliases = resp["Aliases"]

    def has_correct_arn(alias_obj):
        alias_name = alias_obj["AliasName"]
        alias_arn = alias_obj["AliasArn"]
        return re.match(
            r"arn:aws:kms:{region}:\d{{12}}:{alias_name}".format(
                region=region, alias_name=alias_name
            ),
            alias_arn,
        )

    len(
        [
            alias
            for alias in aliases
            if has_correct_arn(alias) and "alias/aws/ebs" == alias["AliasName"]
        ]
    ).should.equal(1)
    len(
        [
            alias
            for alias in aliases
            if has_correct_arn(alias) and "alias/aws/rds" == alias["AliasName"]
        ]
    ).should.equal(1)
    len(
        [
            alias
            for alias in aliases
            if has_correct_arn(alias) and "alias/aws/redshift" == alias["AliasName"]
        ]
    ).should.equal(1)
    len(
        [
            alias
            for alias in aliases
            if has_correct_arn(alias) and "alias/aws/s3" == alias["AliasName"]
        ]
    ).should.equal(1)

    len(
        [
            alias
            for alias in aliases
            if has_correct_arn(alias) and "alias/my-alias1" == alias["AliasName"]
        ]
    ).should.equal(1)
    len(
        [
            alias
            for alias in aliases
            if has_correct_arn(alias) and "alias/my-alias2" == alias["AliasName"]
        ]
    ).should.equal(1)

    len(
        [
            alias
            for alias in aliases
            if "TargetKeyId" in alias and key_id == alias["TargetKeyId"]
        ]
    ).should.equal(3)

    len(aliases).should.equal(17)


@mock_kms_deprecated
def test__assert_default_policy():
    from moto.kms.responses import _assert_default_policy

    _assert_default_policy.when.called_with("not-default").should.throw(
        MotoNotFoundException
    )
    _assert_default_policy.when.called_with("default").should_not.throw(
        MotoNotFoundException
    )


sort = lambda l: sorted(l, key=lambda d: d.keys())


def _check_tags(key_id, created_tags, client):
    result = client.list_resource_tags(KeyId=key_id)
    actual = result.get("Tags", [])
    assert sort(created_tags) == sort(actual)

    client.untag_resource(KeyId=key_id, TagKeys=["key1"])

    actual = client.list_resource_tags(KeyId=key_id).get("Tags", [])
    expected = [{"TagKey": "key2", "TagValue": "value2"}]
    assert sort(expected) == sort(actual)


@mock_kms
def test_key_tag_on_create_key_happy():
    client = boto3.client("kms", region_name="us-east-1")

    tags = [
        {"TagKey": "key1", "TagValue": "value1"},
        {"TagKey": "key2", "TagValue": "value2"},
    ]
    key = client.create_key(Description="test-key-tagging", Tags=tags)
    _check_tags(key["KeyMetadata"]["KeyId"], tags, client)


@mock_kms
def test_key_tag_on_create_key_on_arn_happy():
    client = boto3.client("kms", region_name="us-east-1")

    tags = [
        {"TagKey": "key1", "TagValue": "value1"},
        {"TagKey": "key2", "TagValue": "value2"},
    ]
    key = client.create_key(Description="test-key-tagging", Tags=tags)
    _check_tags(key["KeyMetadata"]["Arn"], tags, client)


@mock_kms
def test_key_tag_added_happy():
    client = boto3.client("kms", region_name="us-east-1")

    key = client.create_key(Description="test-key-tagging")
    key_id = key["KeyMetadata"]["KeyId"]
    tags = [
        {"TagKey": "key1", "TagValue": "value1"},
        {"TagKey": "key2", "TagValue": "value2"},
    ]
    client.tag_resource(KeyId=key_id, Tags=tags)
    _check_tags(key_id, tags, client)


@mock_kms
def test_key_tag_added_arn_based_happy():
    client = boto3.client("kms", region_name="us-east-1")

    key = client.create_key(Description="test-key-tagging")
    key_id = key["KeyMetadata"]["Arn"]
    tags = [
        {"TagKey": "key1", "TagValue": "value1"},
        {"TagKey": "key2", "TagValue": "value2"},
    ]
    client.tag_resource(KeyId=key_id, Tags=tags)
    _check_tags(key_id, tags, client)


# Has boto3 equivalent
@mock_kms_deprecated
def test_key_tagging_sad():
    b = KmsBackend(region="eu-north-1")

    try:
        b.tag_resource("unknown", [])
        raise "tag_resource should fail if KeyId is not known"
    except JsonRESTError:
        pass

    try:
        b.untag_resource("unknown", [])
        raise "untag_resource should fail if KeyId is not known"
    except JsonRESTError:
        pass

    try:
        b.list_resource_tags("unknown")
        raise "list_resource_tags should fail if KeyId is not known"
    except JsonRESTError:
        pass
