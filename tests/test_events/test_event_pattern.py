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
    # The full list should match as well
    assert pattern.matches_event({"detail": {"foo": ["bar"]}})


def test_event_pattern_with_exists_event_filter():
    foo_exists = EventPattern.load(json.dumps({"detail": {"foo": [{"exists": True}]}}))
    assert foo_exists.matches_event({"detail": {"foo": "bar"}})
    assert foo_exists.matches_event({"detail": {"foo": None}})
    assert not foo_exists.matches_event({"detail": {}})
    # exists filters only match leaf nodes of an event
    assert not foo_exists.matches_event({"detail": {"foo": {"bar": "baz"}}})

    foo_not_exists = EventPattern.load(
        json.dumps({"detail": {"foo": [{"exists": False}]}})
    )
    assert not foo_not_exists.matches_event({"detail": {"foo": "bar"}})
    assert not foo_not_exists.matches_event({"detail": {"foo": None}})
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
    [('{"source": ["foo", "bar"]}', '{"source": ["foo", "bar"]}'), (None, None)],
)
def test_event_pattern_dump(pattern, expected_str):
    event_pattern = EventPattern.load(pattern)
    assert event_pattern.dump() == expected_str


def test_event_pattern_matching_with_list_in_event():
    # Pattern with multiple values, event has a scalar that matches one
    pattern = EventPattern.load(
        json.dumps({"detail": {"state": ["running", "stopped"]}})
    )
    assert pattern.matches_event({"detail": {"state": "running"}})
    assert pattern.matches_event({"detail": {"state": "stopped"}})
    assert not pattern.matches_event({"detail": {"state": "pending"}})


def test_event_pattern_matching_with_list_in_event_and_pattern():
    # Pattern with one value, event has a list containing that value
    pattern = EventPattern.load(json.dumps({"detail": {"labels": ["prod"]}}))
    assert pattern.matches_event({"detail": {"labels": ["prod", "web"]}})
    assert not pattern.matches_event({"detail": {"labels": ["test", "web"]}})


def test_event_pattern_matching_with_multiple_values_in_both():
    # Pattern with multiple values, event has a list containing at least one
    pattern = EventPattern.load(json.dumps({"detail": {"tags": ["a", "b"]}}))
    assert pattern.matches_event({"detail": {"tags": ["a", "c"]}})
    assert pattern.matches_event({"detail": {"tags": ["b", "c"]}})
    assert pattern.matches_event({"detail": {"tags": ["a", "b", "c"]}})
    assert not pattern.matches_event({"detail": {"tags": ["c", "d"]}})


def test_event_pattern_exact_list_match():
    # Test that an exact list match also works
    pattern = EventPattern.load(json.dumps({"detail": {"items": ["apple", "orange"]}}))
    assert pattern.matches_event({"detail": {"items": ["apple", "orange"]}})


def test_event_pattern_nested_list_matching():
    # Test nested lists if applicable (though usually EB doesn't have lists of lists in events for patterns)
    pattern = EventPattern.load(json.dumps({"detail": {"nested": {"list": ["val"]}}}))
    assert pattern.matches_event({"detail": {"nested": {"list": ["val", "other"]}}})
    assert not pattern.matches_event({"detail": {"nested": {"list": ["other"]}}})


@pytest.mark.parametrize(
    "pattern_val, event_val, expected",
    [
        (["v1"], ["v1"], True),
        (["v1"], ["v1", "v2"], True),
        (["v1", "v2"], ["v1"], True),
        (["v1", "v2"], ["v3"], False),
        (["v1", "v2"], ["v2", "v3"], True),
        ([1, 2], [2, 3], True),
        ([True], [True, False], True),
        ([1.1], [1.1, 2.2], True),
    ],
)
def test_event_pattern_parameterized_list_matching(pattern_val, event_val, expected):
    pattern = EventPattern.load(json.dumps({"detail": {"field": pattern_val}}))
    assert pattern.matches_event({"detail": {"field": event_val}}) == expected


def test_event_pattern_null_matching():
    pattern = EventPattern.load(json.dumps({"detail": {"field": [None]}}))
    assert pattern.matches_event({"detail": {"field": None}})
    assert not pattern.matches_event({"detail": {"field": "something"}})

    # Pattern with mixed values including null
    pattern = EventPattern.load(json.dumps({"detail": {"field": ["val", None]}}))
    assert pattern.matches_event({"detail": {"field": "val"}})
    assert pattern.matches_event({"detail": {"field": None}})
    assert not pattern.matches_event({"detail": {"field": "other"}})


def test_prefix_matching():
    # Basic prefix
    pattern = EventPattern.load(
        json.dumps({"detail": {"service": [{"prefix": "EventB"}]}})
    )
    assert pattern.matches_event({"detail": {"service": "EventBridge"}})
    assert not pattern.matches_event({"detail": {"service": "Other"}})

    # Prefix ignore case
    pattern = EventPattern.load(
        json.dumps(
            {"detail": {"service": [{"prefix": {"equals-ignore-case": "EventB"}}]}}
        )
    )
    assert pattern.matches_event({"detail": {"service": "eventbridge"}})
    assert pattern.matches_event({"detail": {"service": "EVENTBRIDGE"}})
    assert not pattern.matches_event({"detail": {"service": "Other"}})


def test_suffix_matching():
    # Basic suffix
    pattern = EventPattern.load(
        json.dumps({"detail": {"FileName": [{"suffix": ".png"}]}})
    )
    assert pattern.matches_event({"detail": {"FileName": "image.png"}})
    assert not pattern.matches_event({"detail": {"FileName": "image.jpg"}})

    # Suffix ignore case
    pattern = EventPattern.load(
        json.dumps(
            {"detail": {"FileName": [{"suffix": {"equals-ignore-case": ".png"}}]}}
        )
    )
    assert pattern.matches_event({"detail": {"FileName": "IMAGE.PNG"}})
    assert pattern.matches_event({"detail": {"FileName": "image.png"}})
    assert not pattern.matches_event({"detail": {"FileName": "image.jpg"}})


def test_anything_but_matching_complete():
    # Scalar
    pattern = EventPattern.load(
        json.dumps({"detail": {"state": [{"anything-but": "initializing"}]}})
    )
    assert pattern.matches_event({"detail": {"state": "running"}})
    # No match if exactly prohibited
    assert not pattern.matches_event({"detail": {"state": "initializing"}})

    # List
    pattern = EventPattern.load(
        json.dumps(
            {"detail": {"state": [{"anything-but": ["initializing", "stopped"]}]}}
        )
    )
    assert pattern.matches_event({"detail": {"state": "running"}})
    assert not pattern.matches_event({"detail": {"state": "initializing"}})
    assert not pattern.matches_event({"detail": {"state": "stopped"}})

    # Ignore case
    pattern = EventPattern.load(
        json.dumps(
            {
                "detail": {
                    "state": [{"anything-but": {"equals-ignore-case": "initializing"}}]
                }
            }
        )
    )
    assert pattern.matches_event({"detail": {"state": "running"}})
    assert not pattern.matches_event({"detail": {"state": "INITIALIZING"}})

    # Prefix
    pattern = EventPattern.load(
        json.dumps({"detail": {"state": [{"anything-but": {"prefix": "init"}}]}})
    )
    assert pattern.matches_event({"detail": {"state": "running"}})
    assert not pattern.matches_event({"detail": {"state": "initializing"}})

    # Suffix
    pattern = EventPattern.load(
        json.dumps({"detail": {"FileName": [{"anything-but": {"suffix": ".txt"}}]}})
    )
    assert pattern.matches_event({"detail": {"FileName": "data.json"}})
    assert not pattern.matches_event({"detail": {"FileName": "logs.txt"}})

    # Wildcard
    pattern = EventPattern.load(
        json.dumps(
            {"detail": {"FilePath": [{"anything-but": {"wildcard": "*/lib/*"}}]}}
        )
    )
    assert pattern.matches_event({"detail": {"FilePath": "/usr/bin/exec"}})
    assert not pattern.matches_event({"detail": {"FilePath": "/usr/lib/mod.so"}})


def test_cidr_matching():
    pattern = EventPattern.load(
        json.dumps({"detail": {"sourceIPAddress": [{"cidr": "10.0.0.0/24"}]}})
    )
    assert pattern.matches_event({"detail": {"sourceIPAddress": "10.0.0.123"}})
    assert not pattern.matches_event({"detail": {"sourceIPAddress": "10.0.1.5"}})
    assert not pattern.matches_event({"detail": {"sourceIPAddress": "not-an-ip"}})


def test_equals_ignore_case_matching():
    pattern = EventPattern.load(
        json.dumps(
            {
                "detail-type": [
                    {"equals-ignore-case": "ec2 instance state-change notification"}
                ]
            }
        )
    )
    assert pattern.matches_event(
        {"detail-type": "EC2 Instance State-change Notification"}
    )
    assert not pattern.matches_event({"detail-type": "EC2 Something Else"})


def test_wildcard_matching():
    # Basic wildcard
    pattern = EventPattern.load(
        json.dumps({"detail": {"state": [{"wildcard": "init*"}]}})
    )
    assert pattern.matches_event({"detail": {"state": "initializing"}})
    assert pattern.matches_event({"detail": {"state": "init"}})
    assert not pattern.matches_event({"detail": {"state": "stopped"}})

    # Middle wildcard
    pattern = EventPattern.load(
        json.dumps({"detail": {"path": [{"wildcard": "/usr/*/bin"}]}})
    )
    assert pattern.matches_event({"detail": {"path": "/usr/local/bin"}})
    assert pattern.matches_event({"detail": {"path": "/usr/opt/bin"}})
    assert not pattern.matches_event({"detail": {"path": "/usr/local/lib"}})

    # Escaped wildcard
    pattern = EventPattern.load(
        json.dumps({"detail": {"val": [{"wildcard": "a\\*b"}]}})
    )
    assert pattern.matches_event({"detail": {"val": "a*b"}})
    assert not pattern.matches_event({"detail": {"val": "acb"}})


def test_or_matching():
    # Or at field level
    pattern = EventPattern.load(
        json.dumps(
            {
                "detail": {
                    "$or": [
                        {"c-count": [{"numeric": [">", 0, "<=", 5]}]},
                        {"d-count": [{"numeric": ["<", 10]}]},
                        {"x-limit": [{"numeric": ["=", 301.8]}]},
                    ]
                }
            }
        )
    )
    assert pattern.matches_event({"detail": {"c-count": 3}})
    assert pattern.matches_event({"detail": {"d-count": 5}})
    assert pattern.matches_event({"detail": {"x-limit": 301.8}})
    assert not pattern.matches_event(
        {"detail": {"c-count": 10, "d-count": 20, "x-limit": 500}}
    )


def test_or_matching_top_level():
    pattern = EventPattern.load(
        json.dumps(
            {"$or": [{"source": ["aws.ec2"]}, {"detail": {"state": ["running"]}}]}
        )
    )
    assert pattern.matches_event({"source": "aws.ec2", "detail": {"state": "stopped"}})
    assert pattern.matches_event({"source": "aws.s3", "detail": {"state": "running"}})
    # Support for dot-notation (flattened keys)
    assert pattern.matches_event({"source": "aws.s3", "detail.state": "running"})
    assert not pattern.matches_event(
        {"source": "aws.s3", "detail": {"state": "stopped"}}
    )


def test_nested_list_matching_eb_style():
    # If the event value is an array, it matches if any value matches
    pattern = EventPattern.load(json.dumps({"detail": {"tags": ["a", "b"]}}))
    assert pattern.matches_event({"detail": {"tags": ["a", "c"]}})  # Matches 'a'
    assert pattern.matches_event({"detail": {"tags": ["b", "c"]}})  # Matches 'b'
    assert not pattern.matches_event({"detail": {"tags": ["c", "d"]}})

    # Anything-but with list in event
    pattern = EventPattern.load(
        json.dumps({"detail": {"tags": [{"anything-but": ["a", "b"]}]}})
    )
    assert pattern.matches_event({"detail": {"tags": ["c", "d"]}})
    # This matches because 'c' is anything-but 'a' or 'b'.
    # Array matching in EB is 'any' logic.
    assert pattern.matches_event({"detail": {"tags": ["a", "c"]}})
    assert not pattern.matches_event({"detail": {"tags": ["a", "b"]}})
