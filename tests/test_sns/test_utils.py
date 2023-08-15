import pytest

from moto.sns.utils import FilterPolicyMatcher


def test_filter_policy_matcher_scope_sanity_check():
    with pytest.raises(FilterPolicyMatcher.CheckException):
        FilterPolicyMatcher({}, "IncorrectFilterPolicyScope")


def test_filter_policy_matcher_empty_message_attributes():
    matcher = FilterPolicyMatcher({}, None)
    assert matcher.matches(None, "")


def test_filter_policy_matcher_empty_message_attributes_filtering_fail():
    matcher = FilterPolicyMatcher({"store": ["test"]}, None)
    assert not matcher.matches(None, "")
