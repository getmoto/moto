from collections import namedtuple

import pytest

from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from moto.swf.exceptions import SWFUnknownResourceFault
from moto.swf.models import Domain

TEST_REGION = "us-east-1"
# Fake WorkflowExecution for tests purposes
WorkflowExecution = namedtuple(
    "WorkflowExecution", ["workflow_id", "run_id", "execution_status", "open"]
)


def test_domain_short_dict_representation():
    domain = Domain("foo", "52", ACCOUNT_ID, TEST_REGION)
    assert domain.to_short_dict() == {
        "name": "foo",
        "status": "REGISTERED",
        "arn": f"arn:aws:swf:{TEST_REGION}:{ACCOUNT_ID}:/domain/foo",
    }

    domain.description = "foo bar"
    assert domain.to_short_dict()["description"] == "foo bar"


def test_domain_full_dict_representation():
    domain = Domain("foo", "52", ACCOUNT_ID, TEST_REGION)

    assert domain.to_full_dict()["domainInfo"] == domain.to_short_dict()
    _config = domain.to_full_dict()["configuration"]
    assert _config["workflowExecutionRetentionPeriodInDays"] == "52"


def test_domain_string_representation():
    domain = Domain("my-domain", "60", ACCOUNT_ID, TEST_REGION)
    assert str(domain) == "Domain(name: my-domain, status: REGISTERED)"


def test_domain_add_to_activity_task_list():
    domain = Domain("my-domain", "60", ACCOUNT_ID, TEST_REGION)
    domain.add_to_activity_task_list("foo", "bar")
    assert domain.activity_task_lists == {"foo": ["bar"]}


def test_domain_activity_tasks():
    domain = Domain("my-domain", "60", ACCOUNT_ID, TEST_REGION)
    domain.add_to_activity_task_list("foo", "bar")
    domain.add_to_activity_task_list("other", "baz")
    assert sorted(domain.activity_tasks) == ["bar", "baz"]


def test_domain_add_to_decision_task_list():
    domain = Domain("my-domain", "60", ACCOUNT_ID, TEST_REGION)
    domain.add_to_decision_task_list("foo", "bar")
    assert domain.decision_task_lists == {"foo": ["bar"]}


def test_domain_decision_tasks():
    domain = Domain("my-domain", "60", ACCOUNT_ID, TEST_REGION)
    domain.add_to_decision_task_list("foo", "bar")
    domain.add_to_decision_task_list("other", "baz")
    assert sorted(domain.decision_tasks) == ["bar", "baz"]


def test_domain_get_workflow_execution():
    domain = Domain("my-domain", "60", ACCOUNT_ID, TEST_REGION)

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
    assert domain.get_workflow_execution("wf-id-1", run_id="run-id-1") == wfe1
    assert domain.get_workflow_execution("wf-id-1", run_id="run-id-2") == wfe2
    assert domain.get_workflow_execution("wf-id-3", run_id="run-id-4") == wfe4

    with pytest.raises(SWFUnknownResourceFault):
        domain.get_workflow_execution("wf-id-1", run_id="non-existent")

    # get OPEN workflow execution by default if no run_id
    assert domain.get_workflow_execution("wf-id-1") == wfe1
    with pytest.raises(SWFUnknownResourceFault):
        domain.get_workflow_execution("wf-id-3")
    with pytest.raises(SWFUnknownResourceFault):
        domain.get_workflow_execution("wf-id-non-existent")

    # raise_if_closed attribute
    assert (
        domain.get_workflow_execution(
            "wf-id-1", run_id="run-id-1", raise_if_closed=True
        )
        == wfe1
    )
    with pytest.raises(SWFUnknownResourceFault):
        domain.get_workflow_execution(
            "wf-id-3", run_id="run-id-4", raise_if_closed=True
        )

    # raise_if_none attribute
    assert domain.get_workflow_execution("foo", raise_if_none=False) is None
