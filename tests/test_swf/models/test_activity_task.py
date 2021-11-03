from freezegun import freeze_time
import sure  # noqa # pylint: disable=unused-import

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
        input="optional",
        scheduled_event_id=117,
        workflow_execution=wfe,
        timeouts=ACTIVITY_TASK_TIMEOUTS,
    )
    task.workflow_execution.should.equal(wfe)
    task.state.should.equal("SCHEDULED")
    task.task_token.should_not.be.empty
    task.started_event_id.should.be.none

    task.start(123)
    task.state.should.equal("STARTED")
    task.started_event_id.should.equal(123)

    task.complete()
    task.state.should.equal("COMPLETED")

    # NB: this doesn't make any sense for SWF, a task shouldn't go from a
    # "COMPLETED" state to a "FAILED" one, but this is an internal state on our
    # side and we don't care about invalid state transitions for now.
    task.fail()
    task.state.should.equal("FAILED")


def test_activity_task_full_dict_representation():
    wfe = make_workflow_execution()
    at = ActivityTask(
        activity_id="my-activity-123",
        activity_type=ActivityType("foo", "v1.0"),
        input="optional",
        scheduled_event_id=117,
        timeouts=ACTIVITY_TASK_TIMEOUTS,
        workflow_execution=wfe,
    )
    at.start(1234)

    fd = at.to_full_dict()
    fd["activityId"].should.equal("my-activity-123")
    fd["activityType"]["version"].should.equal("v1.0")
    fd["input"].should.equal("optional")
    fd["startedEventId"].should.equal(1234)
    fd.should.contain("taskToken")
    fd["workflowExecution"].should.equal(wfe.to_short_dict())

    at.start(1234)
    fd = at.to_full_dict()
    fd["startedEventId"].should.equal(1234)


def test_activity_task_reset_heartbeat_clock():
    wfe = make_workflow_execution()

    with freeze_time("2015-01-01 12:00:00"):
        task = ActivityTask(
            activity_id="my-activity-123",
            activity_type="foo",
            input="optional",
            scheduled_event_id=117,
            timeouts=ACTIVITY_TASK_TIMEOUTS,
            workflow_execution=wfe,
        )

    task.last_heartbeat_timestamp.should.equal(1420113600.0)

    with freeze_time("2015-01-01 13:00:00"):
        task.reset_heartbeat_clock()

    task.last_heartbeat_timestamp.should.equal(1420117200.0)


def test_activity_task_first_timeout():
    wfe = make_workflow_execution()

    with freeze_time("2015-01-01 12:00:00"):
        task = ActivityTask(
            activity_id="my-activity-123",
            activity_type="foo",
            input="optional",
            scheduled_event_id=117,
            timeouts=ACTIVITY_TASK_TIMEOUTS,
            workflow_execution=wfe,
        )
        task.first_timeout().should.be.none

    # activity task timeout is 300s == 5mins
    with freeze_time("2015-01-01 12:06:00"):
        task.first_timeout().should.be.a(Timeout)
        process_first_timeout(task)
        task.state.should.equal("TIMED_OUT")
        task.timeout_type.should.equal("HEARTBEAT")


def test_activity_task_first_timeout_with_heartbeat_timeout_none():
    wfe = make_workflow_execution()

    activity_task_timeouts = ACTIVITY_TASK_TIMEOUTS.copy()
    activity_task_timeouts["heartbeatTimeout"] = "NONE"

    with freeze_time("2015-01-01 12:00:00"):
        task = ActivityTask(
            activity_id="my-activity-123",
            activity_type="foo",
            input="optional",
            scheduled_event_id=117,
            timeouts=activity_task_timeouts,
            workflow_execution=wfe,
        )
        task.first_timeout().should.be.none


def test_activity_task_cannot_timeout_on_closed_workflow_execution():
    with freeze_time("2015-01-01 12:00:00"):
        wfe = make_workflow_execution()
        wfe.start()

    with freeze_time("2015-01-01 13:58:00"):
        task = ActivityTask(
            activity_id="my-activity-123",
            activity_type="foo",
            input="optional",
            scheduled_event_id=117,
            timeouts=ACTIVITY_TASK_TIMEOUTS,
            workflow_execution=wfe,
        )

    with freeze_time("2015-01-01 14:10:00"):
        task.first_timeout().should.be.a(Timeout)
        wfe.first_timeout().should.be.a(Timeout)
        process_first_timeout(wfe)
        task.first_timeout().should.be.none


def test_activity_task_cannot_change_state_on_closed_workflow_execution():
    wfe = make_workflow_execution()
    wfe.start()

    task = ActivityTask(
        activity_id="my-activity-123",
        activity_type="foo",
        input="optional",
        scheduled_event_id=117,
        timeouts=ACTIVITY_TASK_TIMEOUTS,
        workflow_execution=wfe,
    )
    wfe.complete(123)

    task.timeout.when.called_with(Timeout(task, 0, "foo")).should.throw(
        SWFWorkflowExecutionClosedError
    )
    task.complete.when.called_with().should.throw(SWFWorkflowExecutionClosedError)
    task.fail.when.called_with().should.throw(SWFWorkflowExecutionClosedError)
