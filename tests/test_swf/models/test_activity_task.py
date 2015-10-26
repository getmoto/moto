from sure import expect

from moto.swf.models import ActivityTask

from ..utils import make_workflow_execution


def test_activity_task_creation():
    wfe = make_workflow_execution()
    task = ActivityTask(
        activity_id="my-activity-123",
        activity_type="foo",
        input="optional",
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
