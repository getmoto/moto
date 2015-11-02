from freezegun import freeze_time
from sure import expect

from moto.swf.models import (
    ActivityTask,
    ActivityType,
)

from ..utils import make_workflow_execution


def test_activity_task_creation():
    wfe = make_workflow_execution()
    task = ActivityTask(
        activity_id="my-activity-123",
        activity_type="foo",
        input="optional",
        scheduled_event_id=117,
        workflow_execution=wfe,
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
            workflow_execution=wfe,
        )

    task.last_heartbeat_timestamp.should.equal(1420110000.0)

    with freeze_time("2015-01-01 13:00:00"):
        task.reset_heartbeat_clock()

    task.last_heartbeat_timestamp.should.equal(1420113600.0)
