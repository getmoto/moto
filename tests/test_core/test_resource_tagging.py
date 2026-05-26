from unittest import SkipTest

import pytest

from moto import mock_aws, settings
from moto.core.resource_tagging import (
    TaggableResourcesMixin,
    TaggedResource,
    iter_taggable_backends,
    make_tag_matcher,
    match_resource_type,
)


class TestInitSubclassValidation:
    def test_subclass_without_service_namespace_raises(self) -> None:
        with pytest.raises(TypeError, match="SERVICE_NAMESPACE"):

            class Bad(TaggableResourcesMixin):
                pass

    def test_subclass_with_service_namespace_is_accepted(self) -> None:
        class Good(TaggableResourcesMixin):
            SERVICE_NAMESPACE = "test"

        assert Good.SERVICE_NAMESPACE == "test"


class TestMatchResourceType:
    def test_no_filters_matches_all(self) -> None:
        assert match_resource_type("rds:cluster", None)
        assert match_resource_type("rds:cluster", [])

    def test_service_prefix_matches_subtype(self) -> None:
        assert match_resource_type("rds:cluster", ["rds"])
        assert match_resource_type("rds:db", ["rds"])

    def test_exact_subtype_matches(self) -> None:
        assert match_resource_type("rds:cluster", ["rds:cluster"])

    def test_exact_subtype_filter_rejects_other_subtypes(self) -> None:
        assert not match_resource_type("rds:db", ["rds:cluster"])

    def test_unrelated_filter_rejects(self) -> None:
        assert not match_resource_type("rds:cluster", ["lambda"])

    def test_multiple_filters_or(self) -> None:
        assert match_resource_type("rds:cluster", ["lambda", "rds"])
        assert match_resource_type("lambda:function", ["lambda", "rds"])
        assert not match_resource_type("s3:bucket", ["lambda", "rds"])


class TestMakeTagMatcher:
    def test_no_filters_matches_anything(self) -> None:
        match = make_tag_matcher(None)
        assert match({})
        assert match({"k": "v"})

    def test_key_only_filter(self) -> None:
        match = make_tag_matcher([{"Key": "env"}])
        assert match({"env": "prod"})
        assert not match({"owner": "team"})

    def test_key_and_value_filter(self) -> None:
        match = make_tag_matcher([{"Key": "env", "Values": ["prod"]}])
        assert match({"env": "prod"})
        assert not match({"env": "dev"})

    def test_multi_value_filter_is_or(self) -> None:
        match = make_tag_matcher([{"Key": "env", "Values": ["prod", "stage"]}])
        assert match({"env": "stage"})
        assert not match({"env": "dev"})

    def test_multiple_filters_are_and(self) -> None:
        match = make_tag_matcher([{"Key": "env", "Values": ["prod"]}, {"Key": "team"}])
        assert match({"env": "prod", "team": "billing"})
        assert not match({"env": "prod"})


@mock_aws
def test_iter_taggable_backends_skips_untouched_accounts() -> None:
    if settings.TEST_SERVER_MODE:
        raise SkipTest("No direct access to backends in Server Mode")

    # Account that's never been touched by any service should yield nothing.
    other_account = list(iter_taggable_backends("999999999999", "us-east-1"))
    assert other_account == []


def test_default_owns_arn() -> None:
    class FakeBackend(TaggableResourcesMixin):
        SERVICE_NAMESPACE = "rds"
        partition = "aws"

    backend = FakeBackend()
    assert backend.owns_arn("arn:aws:rds:us-east-1:123456789012:cluster:foo")
    assert not backend.owns_arn("arn:aws:s3:::bucket")


def test_tagged_resource_dataclass_defaults() -> None:
    r = TaggedResource(arn="arn", tags={}, resource_type="rds:db")
    assert r.extra == {}
