from boto.swf.exceptions import SWFResponseError
from freezegun import freeze_time
from sure import expect

from moto.swf.models import DecisionTask, Timeout
from moto.swf.exceptions import SWFWorkflowExecutionClosedError

from ..utils import make_workflow_execution, process_first_timeout


def test_decision_task_creation():
    wfe = make_workflow_execution()
    dt = DecisionTask(wfe, 123)
    dt.workflow_execution.should.equal(wfe)
    dt.state.should.equal("SCHEDULED")
    dt.task_token.should_not.be.empty
    dt.started_event_id.should.be.none


def test_decision_task_full_dict_representation():
    wfe = make_workflow_execution()
    wft = wfe.workflow_type
    dt = DecisionTask(wfe, 123)

    fd = dt.to_full_dict()
    fd["events"].should.be.a("list")
    fd.should_not.contain("previousStartedEventId")
    fd.should_not.contain("startedEventId")
    fd.should.contain("taskToken")
    fd["workflowExecution"].should.equal(wfe.to_short_dict())
    fd["workflowType"].should.equal(wft.to_short_dict())

    dt.start(1234, 1230)
    fd = dt.to_full_dict()
    fd["startedEventId"].should.equal(1234)
    fd["previousStartedEventId"].should.equal(1230)


def test_decision_task_first_timeout():
    wfe = make_workflow_execution()
    dt = DecisionTask(wfe, 123)
    dt.first_timeout().should.be.none

    with freeze_time("2015-01-01 12:00:00"):
        dt.start(1234)
        dt.first_timeout().should.be.none

    # activity task timeout is 300s == 5mins
    with freeze_time("2015-01-01 12:06:00"):
        dt.first_timeout().should.be.a(Timeout)

    dt.complete()
    dt.first_timeout().should.be.none


def test_decision_task_cannot_timeout_on_closed_workflow_execution():
    with freeze_time("2015-01-01 12:00:00"):
        wfe = make_workflow_execution()
        wfe.start()

    with freeze_time("2015-01-01 13:55:00"):
        dt = DecisionTask(wfe, 123)
        dt.start(1234)

    with freeze_time("2015-01-01 14:10:00"):
        dt.first_timeout().should.be.a(Timeout)
        wfe.first_timeout().should.be.a(Timeout)
        process_first_timeout(wfe)
        dt.first_timeout().should.be.none


def test_decision_task_cannot_change_state_on_closed_workflow_execution():
    wfe = make_workflow_execution()
    wfe.start()
    task = DecisionTask(wfe, 123)

    wfe.complete(123)

    task.timeout.when.called_with(Timeout(task, 0, "foo")).should.throw(
        SWFWorkflowExecutionClosedError
    )
    task.complete.when.called_with().should.throw(SWFWorkflowExecutionClosedError)
