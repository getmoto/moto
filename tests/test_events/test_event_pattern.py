import json

import pytest

from moto.events.models import EventPattern


def test_event_pattern_with_allowed_values_event_filter():
    pattern = EventPattern.load(json.dumps({"source": ["foo", "bar"]}))
    assert pattern.matches_event({"source": "foo"})
    assert pattern.matches_event({"source": "bar"})
    assert not pattern.matches_event({"source": "baz"})


def test_event_pattern_with_nested_event_filter():
    pattern = EventPattern.load(json.dumps({"detail": {"foo": ["bar"]}}))
    assert pattern.matches_event({"detail": {"foo": "bar"}})
    assert not pattern.matches_event({"detail": {"foo": "baz"}})


def test_event_pattern_with_exists_event_filter():
    foo_exists = EventPattern.load(json.dumps({"detail": {"foo": [{"exists": True}]}}))
    assert foo_exists.matches_event({"detail": {"foo": "bar"}})
    assert not foo_exists.matches_event({"detail": {}})
    # exists filters only match leaf nodes of an event
    assert not foo_exists.matches_event({"detail": {"foo": {"bar": "baz"}}})

    foo_not_exists = EventPattern.load(
        json.dumps({"detail": {"foo": [{"exists": False}]}})
    )
    assert not foo_not_exists.matches_event({"detail": {"foo": "bar"}})
    assert foo_not_exists.matches_event({"detail": {}})
    assert foo_not_exists.matches_event({"detail": {"foo": {"bar": "baz"}}})

    bar_exists = EventPattern.load(json.dumps({"detail": {"bar": [{"exists": True}]}}))
    assert not bar_exists.matches_event({"detail": {"foo": "bar"}})
    assert not bar_exists.matches_event({"detail": {}})

    bar_not_exists = EventPattern.load(
        json.dumps({"detail": {"bar": [{"exists": False}]}})
    )
    assert bar_not_exists.matches_event({"detail": {"foo": "bar"}})
    assert bar_not_exists.matches_event({"detail": {}})


def test_event_pattern_with_prefix_event_filter():
    pattern = EventPattern.load(json.dumps({"detail": {"foo": [{"prefix": "bar"}]}}))
    assert pattern.matches_event({"detail": {"foo": "bar"}})
    assert pattern.matches_event({"detail": {"foo": "bar!"}})
    assert not pattern.matches_event({"detail": {"foo": "ba"}})


@pytest.mark.parametrize(
    "operator, compare_to, should_match, should_not_match",
    [
        ("<", 1, [0], [1, 2]),
        ("<=", 1, [0, 1], [2]),
        ("=", 1, [1], [0, 2]),
        (">", 1, [2], [0, 1]),
        (">=", 1, [1, 2], [0]),
    ],
)
def test_event_pattern_with_single_numeric_event_filter(
    operator, compare_to, should_match, should_not_match
):
    pattern = EventPattern.load(
        json.dumps({"detail": {"foo": [{"numeric": [operator, compare_to]}]}})
    )
    for number in should_match:
        assert pattern.matches_event({"detail": {"foo": number}})
    for number in should_not_match:
        assert not pattern.matches_event({"detail": {"foo": number}})


def test_event_pattern_with_multi_numeric_event_filter():
    events = [{"detail": {"foo": number}} for number in range(5)]

    one_or_two = EventPattern.load(
        json.dumps({"detail": {"foo": [{"numeric": [">=", 1, "<", 3]}]}})
    )
    assert not one_or_two.matches_event(events[0])
    assert one_or_two.matches_event(events[1])
    assert one_or_two.matches_event(events[2])
    assert not one_or_two.matches_event(events[3])
    assert not one_or_two.matches_event(events[4])

    two_or_three = EventPattern.load(
        json.dumps({"detail": {"foo": [{"numeric": [">", 1, "<=", 3]}]}})
    )
    assert not two_or_three.matches_event(events[0])
    assert not two_or_three.matches_event(events[1])
    assert two_or_three.matches_event(events[2])
    assert two_or_three.matches_event(events[3])
    assert not two_or_three.matches_event(events[4])


@pytest.mark.parametrize(
    "pattern, expected_str",
    [('{"source": ["foo", "bar"]}', '{"source": ["foo", "bar"]}'), (None, None),],
)
def test_event_pattern_dump(pattern, expected_str):
    event_pattern = EventPattern.load(pattern)
    assert event_pattern.dump() == expected_str
