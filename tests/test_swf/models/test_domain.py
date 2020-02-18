from collections import namedtuple
import sure  # noqa

from moto.swf.exceptions import SWFUnknownResourceFault
from moto.swf.models import Domain

# Ensure 'assert_raises' context manager support for Python 2.6
import tests.backport_assert_raises  # noqa

# Fake WorkflowExecution for tests purposes
WorkflowExecution = namedtuple(
    "WorkflowExecution", ["workflow_id", "run_id", "execution_status", "open"]
)


def test_domain_short_dict_representation():
    domain = Domain("foo", "52")
    domain.to_short_dict().should.equal({"name": "foo", "status": "REGISTERED"})

    domain.description = "foo bar"
    domain.to_short_dict()["description"].should.equal("foo bar")


def test_domain_full_dict_representation():
    domain = Domain("foo", "52")

    domain.to_full_dict()["domainInfo"].should.equal(domain.to_short_dict())
    _config = domain.to_full_dict()["configuration"]
    _config["workflowExecutionRetentionPeriodInDays"].should.equal("52")


def test_domain_string_representation():
    domain = Domain("my-domain", "60")
    str(domain).should.equal("Domain(name: my-domain, status: REGISTERED)")


def test_domain_add_to_activity_task_list():
    domain = Domain("my-domain", "60")
    domain.add_to_activity_task_list("foo", "bar")
    domain.activity_task_lists.should.equal({"foo": ["bar"]})


def test_domain_activity_tasks():
    domain = Domain("my-domain", "60")
    domain.add_to_activity_task_list("foo", "bar")
    domain.add_to_activity_task_list("other", "baz")
    sorted(domain.activity_tasks).should.equal(["bar", "baz"])


def test_domain_add_to_decision_task_list():
    domain = Domain("my-domain", "60")
    domain.add_to_decision_task_list("foo", "bar")
    domain.decision_task_lists.should.equal({"foo": ["bar"]})


def test_domain_decision_tasks():
    domain = Domain("my-domain", "60")
    domain.add_to_decision_task_list("foo", "bar")
    domain.add_to_decision_task_list("other", "baz")
    sorted(domain.decision_tasks).should.equal(["bar", "baz"])


def test_domain_get_workflow_execution():
    domain = Domain("my-domain", "60")

    wfe1 = WorkflowExecution(
        workflow_id="wf-id-1", run_id="run-id-1", execution_status="OPEN", open=True
    )
    wfe2 = WorkflowExecution(
        workflow_id="wf-id-1", run_id="run-id-2", execution_status="CLOSED", open=False
    )
    wfe3 = WorkflowExecution(
        workflow_id="wf-id-2", run_id="run-id-3", execution_status="OPEN", open=True
    )
    wfe4 = WorkflowExecution(
        workflow_id="wf-id-3", run_id="run-id-4", execution_status="CLOSED", open=False
    )
    domain.workflow_executions = [wfe1, wfe2, wfe3, wfe4]

    # get workflow execution through workflow_id and run_id
    domain.get_workflow_execution("wf-id-1", run_id="run-id-1").should.equal(wfe1)
    domain.get_workflow_execution("wf-id-1", run_id="run-id-2").should.equal(wfe2)
    domain.get_workflow_execution("wf-id-3", run_id="run-id-4").should.equal(wfe4)

    domain.get_workflow_execution.when.called_with(
        "wf-id-1", run_id="non-existent"
    ).should.throw(SWFUnknownResourceFault)

    # get OPEN workflow execution by default if no run_id
    domain.get_workflow_execution("wf-id-1").should.equal(wfe1)
    domain.get_workflow_execution.when.called_with("wf-id-3").should.throw(
        SWFUnknownResourceFault
    )
    domain.get_workflow_execution.when.called_with("wf-id-non-existent").should.throw(
        SWFUnknownResourceFault
    )

    # raise_if_closed attribute
    domain.get_workflow_execution(
        "wf-id-1", run_id="run-id-1", raise_if_closed=True
    ).should.equal(wfe1)
    domain.get_workflow_execution.when.called_with(
        "wf-id-3", run_id="run-id-4", raise_if_closed=True
    ).should.throw(SWFUnknownResourceFault)

    # raise_if_none attribute
    domain.get_workflow_execution("foo", raise_if_none=False).should.be.none
