import re

import pytest
from freezegun import freeze_time

from moto.swf.exceptions import SWFWorkflowExecutionClosedError
from moto.swf.models import DecisionTask, Timeout

from ..utils import make_workflow_execution, process_first_timeout


def test_decision_task_creation():
    wfe = make_workflow_execution()
    dt = DecisionTask(wfe, 123)
    assert dt.workflow_execution == wfe
    assert dt.state == "SCHEDULED"
    assert re.match("[-a-z0-9]+", dt.task_token)
    assert dt.started_event_id is None


def test_decision_task_full_dict_representation():
    wfe = make_workflow_execution()
    wft = wfe.workflow_type
    dt = DecisionTask(wfe, 123)

    fd = dt.to_full_dict()
    assert isinstance(fd["events"], list)
    assert "previousStartedEventId" not in fd
    assert "startedEventId" not in fd
    assert "taskToken" in fd
    assert fd["workflowExecution"] == wfe.to_short_dict()
    assert fd["workflowType"] == wft.to_short_dict()

    dt.start(1234, 1230)
    fd = dt.to_full_dict()
    assert fd["startedEventId"] == 1234
    assert fd["previousStartedEventId"] == 1230


def test_decision_task_first_timeout():
    wfe = make_workflow_execution()
    dt = DecisionTask(wfe, 123)
    assert dt.first_timeout() is None

    with freeze_time("2015-01-01 12:00:00"):
        dt.start(1234)
        assert dt.first_timeout() is None

    # activity task timeout is 300s == 5mins
    with freeze_time("2015-01-01 12:06:00"):
        assert isinstance(dt.first_timeout(), Timeout)

    dt.complete()
    assert dt.first_timeout() is None


def test_decision_task_cannot_timeout_on_closed_workflow_execution():
    with freeze_time("2015-01-01 12:00:00"):
        wfe = make_workflow_execution()
        wfe.start()

    with freeze_time("2015-01-01 13:55:00"):
        dt = DecisionTask(wfe, 123)
        dt.start(1234)

    with freeze_time("2015-01-01 14:10:00"):
        assert isinstance(dt.first_timeout(), Timeout)
        assert isinstance(wfe.first_timeout(), Timeout)
        process_first_timeout(wfe)
        assert dt.first_timeout() is None


def test_decision_task_cannot_change_state_on_closed_workflow_execution():
    wfe = make_workflow_execution()
    wfe.start()
    task = DecisionTask(wfe, 123)

    wfe.complete(123)

    with pytest.raises(SWFWorkflowExecutionClosedError):
        task.timeout(Timeout(task, 0, "foo"))
    with pytest.raises(SWFWorkflowExecutionClosedError):
        task.complete()
