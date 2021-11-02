from freezegun import freeze_time
import sure  # noqa # pylint: disable=unused-import

from moto.swf.models import HistoryEvent


@freeze_time("2015-01-01 12:00:00")
def test_history_event_creation():
    he = HistoryEvent(123, "DecisionTaskStarted", scheduled_event_id=2)
    he.event_id.should.equal(123)
    he.event_type.should.equal("DecisionTaskStarted")
    he.event_timestamp.should.equal(1420113600.0)


@freeze_time("2015-01-01 12:00:00")
def test_history_event_to_dict_representation():
    he = HistoryEvent(123, "DecisionTaskStarted", scheduled_event_id=2)
    he.to_dict().should.equal(
        {
            "eventId": 123,
            "eventType": "DecisionTaskStarted",
            "eventTimestamp": 1420113600.0,
            "decisionTaskStartedEventAttributes": {"scheduledEventId": 2},
        }
    )


def test_history_event_breaks_on_initialization_if_not_implemented():
    HistoryEvent.when.called_with(123, "UnknownHistoryEvent").should.throw(
        NotImplementedError
    )
