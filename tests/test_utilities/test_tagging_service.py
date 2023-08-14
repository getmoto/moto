"""Unit tests for the TaggingService class."""
from moto.utilities.tagging_service import TaggingService


def test_list_empty():
    svc = TaggingService()
    result = svc.list_tags_for_resource("test")

    assert {"Tags": []} == result


def test_create_tag():
    svc = TaggingService("TheTags", "TagKey", "TagValue")
    tags = [{"TagKey": "key_key", "TagValue": "value_value"}]
    svc.tag_resource("arn", tags)
    actual = svc.list_tags_for_resource("arn")
    expected = {"TheTags": [{"TagKey": "key_key", "TagValue": "value_value"}]}

    assert expected == actual


def test_create_tag_without_value():
    svc = TaggingService()
    tags = [{"Key": "key_key"}]
    svc.tag_resource("arn", tags)
    actual = svc.list_tags_for_resource("arn")
    expected = {"Tags": [{"Key": "key_key", "Value": None}]}

    assert expected == actual


def test_delete_tag_using_names():
    svc = TaggingService()
    tags = [{"Key": "key_key", "Value": "value_value"}]
    svc.tag_resource("arn", tags)
    svc.untag_resource_using_names("arn", ["key_key"])
    result = svc.list_tags_for_resource("arn")

    assert {"Tags": []} == result


def test_delete_all_tags_for_resource():
    svc = TaggingService()
    tags = [{"Key": "key_key", "Value": "value_value"}]
    tags2 = [{"Key": "key_key2", "Value": "value_value2"}]
    svc.tag_resource("arn", tags)
    svc.tag_resource("arn", tags2)
    svc.delete_all_tags_for_resource("arn")
    result = svc.list_tags_for_resource("arn")

    assert {"Tags": []} == result


def test_list_empty_delete():
    svc = TaggingService()
    svc.untag_resource_using_names("arn", ["key_key"])
    result = svc.list_tags_for_resource("arn")

    assert {"Tags": []} == result


def test_delete_tag_using_tags():
    svc = TaggingService()
    tags = [{"Key": "key_key", "Value": "value_value"}]
    svc.tag_resource("arn", tags)
    svc.untag_resource_using_tags("arn", tags)
    result = svc.list_tags_for_resource("arn")

    assert {"Tags": []} == result


def test_extract_tag_names():
    svc = TaggingService()
    tags = [{"Key": "key1", "Value": "value1"}, {"Key": "key2", "Value": "value2"}]
    actual = svc.extract_tag_names(tags)
    expected = ["key1", "key2"]

    assert expected == actual


def test_copy_non_existing_arn():
    svc = TaggingService()
    tags = [{"Key": "key1", "Value": "value1"}, {"Key": "key2", "Value": "value2"}]
    svc.tag_resource("new_arn", tags)
    #
    svc.copy_tags("non_existing_arn", "new_arn")
    # Copying from a non-existing ARN should a NOOP
    # Assert the old tags still exist
    actual = sorted(
        svc.list_tags_for_resource("new_arn")["Tags"], key=lambda t: t["Key"]
    )
    assert actual == tags


def test_copy_existing_arn():
    svc = TaggingService()
    tags_old_arn = [{"Key": "key1", "Value": "value1"}]
    tags_new_arn = [{"Key": "key2", "Value": "value2"}]
    svc.tag_resource("old_arn", tags_old_arn)
    svc.tag_resource("new_arn", tags_new_arn)
    #
    svc.copy_tags("old_arn", "new_arn")
    # Assert the old tags still exist
    actual = sorted(
        svc.list_tags_for_resource("new_arn")["Tags"], key=lambda t: t["Key"]
    )
    assert actual == [
        {"Key": "key1", "Value": "value1"},
        {"Key": "key2", "Value": "value2"},
    ]


def test_validate_tags():
    """Unit tests for validate_tags()."""
    svc = TaggingService()
    # Key with invalid characters.
    errors = svc.validate_tags([{"Key": "foo!", "Value": "bar"}])
    assert (
        "Value 'foo!' at 'tags.1.member.key' failed to satisfy constraint: "
        "Member must satisfy regular expression pattern"
    ) in errors

    # Value with invalid characters.
    errors = svc.validate_tags([{"Key": "foo", "Value": "bar!"}])
    assert (
        "Value 'bar!' at 'tags.1.member.value' failed to satisfy "
        "constraint: Member must satisfy regular expression pattern"
    ) in errors

    # Key too long.
    errors = svc.validate_tags(
        [
            {
                "Key": (
                    "12345678901234567890123456789012345678901234567890"
                    "12345678901234567890123456789012345678901234567890"
                    "123456789012345678901234567890"
                ),
                "Value": "foo",
            }
        ]
    )
    assert (
        "at 'tags.1.member.key' failed to satisfy constraint: Member must "
        "have length less than or equal to 128"
    ) in errors

    # Value too long.
    errors = svc.validate_tags(
        [
            {
                "Key": "foo",
                "Value": (
                    "12345678901234567890123456789012345678901234567890"
                    "12345678901234567890123456789012345678901234567890"
                    "12345678901234567890123456789012345678901234567890"
                    "12345678901234567890123456789012345678901234567890"
                    "12345678901234567890123456789012345678901234567890"
                    "1234567890"
                ),
            },
        ]
    )
    assert (
        "at 'tags.1.member.value' failed to satisfy constraint: Member "
        "must have length less than or equal to 256"
    ) in errors

    # Compound errors.
    errors = svc.validate_tags(
        [
            {
                "Key": (
                    "12345678901234567890123456789012345678901234567890"
                    "12345678901234567890123456789012345678901234567890"
                    "123456789012345678901234567890"
                ),
                "Value": (
                    "12345678901234567890123456789012345678901234567890"
                    "12345678901234567890123456789012345678901234567890"
                    "12345678901234567890123456789012345678901234567890"
                    "12345678901234567890123456789012345678901234567890"
                    "12345678901234567890123456789012345678901234567890"
                    "1234567890"
                ),
            },
            {"Key": "foo!", "Value": "bar!"},
        ]
    )
    assert "4 validation errors detected" in errors
    assert (
        "at 'tags.1.member.key' failed to satisfy constraint: Member must "
        "have length less than or equal to 128"
    ) in errors
    assert (
        "at 'tags.1.member.value' failed to satisfy constraint: Member "
        "must have length less than or equal to 256"
    ) in errors
    assert (
        "Value 'foo!' at 'tags.2.member.key' failed to satisfy constraint: "
        "Member must satisfy regular expression pattern"
    ) in errors
    assert (
        "Value 'bar!' at 'tags.2.member.value' failed to satisfy "
        "constraint: Member must satisfy regular expression pattern"
    ) in errors
