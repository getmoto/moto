from sure import expect

from moto.swf.models import DecisionTask

from ..utils import make_workflow_execution


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
    fd["previousStartedEventId"].should.equal(0)
    fd.should_not.contain("startedEventId")
    fd.should.contain("taskToken")
    fd["workflowExecution"].should.equal(wfe.to_short_dict())
    fd["workflowType"].should.equal(wft.to_short_dict())

    dt.start(1234)
    fd = dt.to_full_dict()
    fd["startedEventId"].should.equal(1234)
