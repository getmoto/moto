import re

from freezegun import freeze_time
import pytest

from moto.swf.exceptions import SWFWorkflowExecutionClosedError
from moto.swf.models import ActivityTask, ActivityType, Timeout

from ..utils import (
    ACTIVITY_TASK_TIMEOUTS,
    make_workflow_execution,
    process_first_timeout,
)


def test_activity_task_creation():
    wfe = make_workflow_execution()
    task = ActivityTask(
        activity_id="my-activity-123",
        activity_type="foo",
        workflow_input="optional",
        scheduled_event_id=117,
        workflow_execution=wfe,
        timeouts=ACTIVITY_TASK_TIMEOUTS,
    )
    assert task.workflow_execution == wfe
    assert task.state == "SCHEDULED"
    assert re.match("[-a-z0-9]+", task.task_token)
    assert task.started_event_id is None

    task.start(123)
    assert task.state == "STARTED"
    assert task.started_event_id == 123

    task.complete()
    assert task.state == "COMPLETED"

    # NB: this doesn't make any sense for SWF, a task shouldn't go from a
    # "COMPLETED" state to a "FAILED" one, but this is an internal state on our
    # side and we don't care about invalid state transitions for now.
    task.fail()
    assert task.state == "FAILED"


def test_activity_task_full_dict_representation():
    wfe = make_workflow_execution()
    at = ActivityTask(
        activity_id="my-activity-123",
        activity_type=ActivityType("foo", "v1.0"),
        workflow_input="optional",
        scheduled_event_id=117,
        timeouts=ACTIVITY_TASK_TIMEOUTS,
        workflow_execution=wfe,
    )
    at.start(1234)

    fd = at.to_full_dict()
    assert fd["activityId"] == "my-activity-123"
    assert fd["activityType"]["version"] == "v1.0"
    assert fd["input"] == "optional"
    assert fd["startedEventId"] == 1234
    assert "taskToken" in fd
    assert fd["workflowExecution"] == wfe.to_short_dict()

    at.start(1234)
    fd = at.to_full_dict()
    assert fd["startedEventId"] == 1234


def test_activity_task_reset_heartbeat_clock():
    wfe = make_workflow_execution()

    with freeze_time("2015-01-01 12:00:00"):
        task = ActivityTask(
            activity_id="my-activity-123",
            activity_type="foo",
            workflow_input="optional",
            scheduled_event_id=117,
            timeouts=ACTIVITY_TASK_TIMEOUTS,
            workflow_execution=wfe,
        )

    assert task.last_heartbeat_timestamp == 1420113600.0

    with freeze_time("2015-01-01 13:00:00"):
        task.reset_heartbeat_clock()

    assert task.last_heartbeat_timestamp == 1420117200.0


def test_activity_task_first_timeout():
    wfe = make_workflow_execution()

    with freeze_time("2015-01-01 12:00:00"):
        task = ActivityTask(
            activity_id="my-activity-123",
            activity_type="foo",
            workflow_input="optional",
            scheduled_event_id=117,
            timeouts=ACTIVITY_TASK_TIMEOUTS,
            workflow_execution=wfe,
        )
        assert task.first_timeout() is None

    # activity task timeout is 300s == 5mins
    with freeze_time("2015-01-01 12:06:00"):
        assert isinstance(task.first_timeout(), Timeout)
        process_first_timeout(task)
        assert task.state == "TIMED_OUT"
        assert task.timeout_type == "HEARTBEAT"


def test_activity_task_first_timeout_with_heartbeat_timeout_none():
    wfe = make_workflow_execution()

    activity_task_timeouts = ACTIVITY_TASK_TIMEOUTS.copy()
    activity_task_timeouts["heartbeatTimeout"] = "NONE"

    with freeze_time("2015-01-01 12:00:00"):
        task = ActivityTask(
            activity_id="my-activity-123",
            activity_type="foo",
            workflow_input="optional",
            scheduled_event_id=117,
            timeouts=activity_task_timeouts,
            workflow_execution=wfe,
        )
        assert task.first_timeout() is None


def test_activity_task_cannot_timeout_on_closed_workflow_execution():
    with freeze_time("2015-01-01 12:00:00"):
        wfe = make_workflow_execution()
        wfe.start()

    with freeze_time("2015-01-01 13:58:00"):
        task = ActivityTask(
            activity_id="my-activity-123",
            activity_type="foo",
            workflow_input="optional",
            scheduled_event_id=117,
            timeouts=ACTIVITY_TASK_TIMEOUTS,
            workflow_execution=wfe,
        )

    with freeze_time("2015-01-01 14:10:00"):
        assert isinstance(task.first_timeout(), Timeout)
        assert isinstance(wfe.first_timeout(), Timeout)
        process_first_timeout(wfe)
        assert task.first_timeout() is None


def test_activity_task_cannot_change_state_on_closed_workflow_execution():
    wfe = make_workflow_execution()
    wfe.start()

    task = ActivityTask(
        activity_id="my-activity-123",
        activity_type="foo",
        workflow_input="optional",
        scheduled_event_id=117,
        timeouts=ACTIVITY_TASK_TIMEOUTS,
        workflow_execution=wfe,
    )
    wfe.complete(123)

    with pytest.raises(SWFWorkflowExecutionClosedError):
        task.timeout(Timeout(task, 0, "foo"))
    with pytest.raises(SWFWorkflowExecutionClosedError):
        task.complete()
    with pytest.raises(SWFWorkflowExecutionClosedError):
        task.fail()
