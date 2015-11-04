from freezegun import freeze_time
from sure import expect

from moto.swf.models import (
    ActivityTask,
    ActivityType,
)

from ..utils import make_workflow_execution, ACTIVITY_TASK_TIMEOUTS


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
    wft = wfe.workflow_type
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

def test_activity_task_has_timedout():
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
        task.has_timedout().should.equal(False)

    # activity task timeout is 300s == 5mins
    with freeze_time("2015-01-01 12:06:00"):
        task.has_timedout().should.equal(True)
        task.process_timeouts()
        task.state.should.equal("TIMED_OUT")
        task.timeout_type.should.equal("HEARTBEAT")

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
        task.has_timedout().should.equal(True)
        wfe.has_timedout().should.equal(True)
        wfe.process_timeouts()
        task.has_timedout().should.equal(False)
