import pytest
from freezegun import freeze_time

from moto.swf.models import HistoryEvent


@freeze_time("2015-01-01 12:00:00")
def test_history_event_creation():
    he = HistoryEvent(123, "DecisionTaskStarted", scheduled_event_id=2)
    assert he.event_id == 123
    assert he.event_type == "DecisionTaskStarted"
    assert he.event_timestamp == 1420113600.0


@freeze_time("2015-01-01 12:00:00")
def test_history_event_to_dict_representation():
    he = HistoryEvent(123, "DecisionTaskStarted", scheduled_event_id=2)
    assert he.to_dict() == {
        "eventId": 123,
        "eventType": "DecisionTaskStarted",
        "eventTimestamp": 1420113600.0,
        "decisionTaskStartedEventAttributes": {"scheduledEventId": 2},
    }


def test_history_event_breaks_on_initialization_if_not_implemented():
    with pytest.raises(NotImplementedError):
        HistoryEvent(123, "UnknownHistoryEvent")
