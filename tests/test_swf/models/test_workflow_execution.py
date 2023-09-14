import re
from threading import Timer as ThreadingTimer
from time import sleep
from unittest.mock import Mock, patch

from freezegun import freeze_time
import pytest

from moto.swf.exceptions import SWFDefaultUndefinedFault
from moto.swf.models import (
    ActivityType,
    Timeout,
    Timer,
    WorkflowType,
    WorkflowExecution,
)
from ..utils import (
    auto_start_decision_tasks,
    get_basic_domain,
    get_basic_workflow_type,
    make_workflow_execution,
)


VALID_ACTIVITY_TASK_ATTRIBUTES = {
    "activityId": "my-activity-001",
    "activityType": {"name": "test-activity", "version": "v1.1"},
    "taskList": {"name": "task-list-name"},
    "scheduleToStartTimeout": "600",
    "scheduleToCloseTimeout": "600",
    "startToCloseTimeout": "600",
    "heartbeatTimeout": "300",
}


def test_workflow_execution_creation():
    domain = get_basic_domain()
    wft = get_basic_workflow_type()
    wfe = WorkflowExecution(domain, wft, "ab1234", child_policy="TERMINATE")

    assert wfe.domain == domain
    assert wfe.workflow_type == wft
    assert wfe.child_policy == "TERMINATE"


def test_workflow_execution_creation_child_policy_logic():
    domain = get_basic_domain()

    assert (
        WorkflowExecution(
            domain,
            WorkflowType(
                "test-workflow",
                "v1.0",
                task_list="queue",
                default_child_policy="ABANDON",
                default_execution_start_to_close_timeout="300",
                default_task_start_to_close_timeout="300",
            ),
            "ab1234",
        ).child_policy
        == "ABANDON"
    )

    assert (
        WorkflowExecution(
            domain,
            WorkflowType(
                "test-workflow",
                "v1.0",
                task_list="queue",
                default_execution_start_to_close_timeout="300",
                default_task_start_to_close_timeout="300",
            ),
            "ab1234",
            child_policy="REQUEST_CANCEL",
        ).child_policy
        == "REQUEST_CANCEL"
    )

    with pytest.raises(SWFDefaultUndefinedFault):
        WorkflowExecution(domain, WorkflowType("test-workflow", "v1.0"), "ab1234")


def test_workflow_execution_string_representation():
    wfe = make_workflow_execution(child_policy="TERMINATE")
    assert re.match(r"^WorkflowExecution\(run_id: .*\)", str(wfe))


def test_workflow_execution_generates_a_random_run_id():
    domain = get_basic_domain()
    wft = get_basic_workflow_type()
    wfe1 = WorkflowExecution(domain, wft, "ab1234", child_policy="TERMINATE")
    wfe2 = WorkflowExecution(domain, wft, "ab1235", child_policy="TERMINATE")
    assert wfe1.run_id != wfe2.run_id


def test_workflow_execution_short_dict_representation():
    domain = get_basic_domain()
    wf_type = WorkflowType(
        "test-workflow",
        "v1.0",
        task_list="queue",
        default_child_policy="ABANDON",
        default_execution_start_to_close_timeout="300",
        default_task_start_to_close_timeout="300",
    )
    wfe = WorkflowExecution(domain, wf_type, "ab1234")

    sd = wfe.to_short_dict()
    assert sd["workflowId"] == "ab1234"
    assert "runId" in sd


def test_workflow_execution_medium_dict_representation():
    domain = get_basic_domain()
    wf_type = WorkflowType(
        "test-workflow",
        "v1.0",
        task_list="queue",
        default_child_policy="ABANDON",
        default_execution_start_to_close_timeout="300",
        default_task_start_to_close_timeout="300",
    )
    wfe = WorkflowExecution(domain, wf_type, "ab1234")

    md = wfe.to_medium_dict()
    assert md["execution"] == wfe.to_short_dict()
    assert md["workflowType"] == wf_type.to_short_dict()
    assert isinstance(md["startTimestamp"], float)
    assert md["executionStatus"] == "OPEN"
    assert md["cancelRequested"] is False
    assert "tagList" not in md

    wfe.tag_list = ["foo", "bar", "baz"]
    md = wfe.to_medium_dict()
    assert md["tagList"] == ["foo", "bar", "baz"]


def test_workflow_execution_full_dict_representation():
    domain = get_basic_domain()
    wf_type = WorkflowType(
        "test-workflow",
        "v1.0",
        task_list="queue",
        default_child_policy="ABANDON",
        default_execution_start_to_close_timeout="300",
        default_task_start_to_close_timeout="300",
    )
    wfe = WorkflowExecution(domain, wf_type, "ab1234")

    fd = wfe.to_full_dict()
    assert fd["executionInfo"] == wfe.to_medium_dict()
    assert fd["openCounts"]["openTimers"] == 0
    assert fd["openCounts"]["openDecisionTasks"] == 0
    assert fd["openCounts"]["openActivityTasks"] == 0
    assert fd["executionConfiguration"] == {
        "childPolicy": "ABANDON",
        "executionStartToCloseTimeout": "300",
        "taskList": {"name": "queue"},
        "taskStartToCloseTimeout": "300",
    }


def test_closed_workflow_execution_full_dict_representation():
    domain = get_basic_domain()
    wf_type = WorkflowType(
        "test-workflow",
        "v1.0",
        task_list="queue",
        default_child_policy="ABANDON",
        default_execution_start_to_close_timeout="300",
        default_task_start_to_close_timeout="300",
    )
    wfe = WorkflowExecution(domain, wf_type, "ab1234")
    wfe.execution_status = "CLOSED"
    wfe.close_status = "CANCELED"
    wfe.close_timestamp = 1420066801.123

    fd = wfe.to_full_dict()
    medium_dict = wfe.to_medium_dict()
    medium_dict["closeStatus"] = "CANCELED"
    medium_dict["closeTimestamp"] = 1420066801.123
    assert fd["executionInfo"] == medium_dict
    assert fd["openCounts"]["openTimers"] == 0
    assert fd["openCounts"]["openDecisionTasks"] == 0
    assert fd["openCounts"]["openActivityTasks"] == 0
    assert fd["executionConfiguration"] == {
        "childPolicy": "ABANDON",
        "executionStartToCloseTimeout": "300",
        "taskList": {"name": "queue"},
        "taskStartToCloseTimeout": "300",
    }


def test_workflow_execution_list_dict_representation():
    domain = get_basic_domain()
    wf_type = WorkflowType(
        "test-workflow",
        "v1.0",
        task_list="queue",
        default_child_policy="ABANDON",
        default_execution_start_to_close_timeout="300",
        default_task_start_to_close_timeout="300",
    )
    wfe = WorkflowExecution(domain, wf_type, "ab1234")

    ld = wfe.to_list_dict()
    assert ld["workflowType"]["version"] == "v1.0"
    assert ld["workflowType"]["name"] == "test-workflow"
    assert ld["executionStatus"] == "OPEN"
    assert ld["execution"]["workflowId"] == "ab1234"
    assert "runId" in ld["execution"]
    assert ld["cancelRequested"] is False
    assert "startTimestamp" in ld


def test_workflow_execution_schedule_decision_task():
    wfe = make_workflow_execution()
    assert wfe.open_counts["openDecisionTasks"] == 0
    wfe.schedule_decision_task()
    assert wfe.open_counts["openDecisionTasks"] == 1


def test_workflow_execution_dont_schedule_decision_if_existing_started_and_other_scheduled():
    wfe = make_workflow_execution()
    assert wfe.open_counts["openDecisionTasks"] == 0

    wfe.schedule_decision_task()
    assert wfe.open_counts["openDecisionTasks"] == 1

    wfe.decision_tasks[0].start("evt_id")

    wfe.schedule_decision_task()
    wfe.schedule_decision_task()
    assert wfe.open_counts["openDecisionTasks"] == 2


def test_workflow_execution_schedule_decision_if_existing_started_and_no_other_scheduled():
    wfe = make_workflow_execution()
    assert wfe.open_counts["openDecisionTasks"] == 0

    wfe.schedule_decision_task()
    assert wfe.open_counts["openDecisionTasks"] == 1

    wfe.decision_tasks[0].start("evt_id")

    wfe.schedule_decision_task()
    assert wfe.open_counts["openDecisionTasks"] == 2


def test_workflow_execution_start_decision_task():
    wfe = make_workflow_execution()
    wfe.schedule_decision_task()
    dt = wfe.decision_tasks[0]
    wfe.start_decision_task(dt.task_token, identity="srv01")
    dt = wfe.decision_tasks[0]
    assert dt.state == "STARTED"
    assert wfe.events()[-1].event_type == "DecisionTaskStarted"
    assert wfe.events()[-1].event_attributes["identity"] == "srv01"


def test_workflow_execution_history_events_ids():
    wfe = make_workflow_execution()
    wfe._add_event("WorkflowExecutionStarted")
    wfe._add_event("DecisionTaskScheduled")
    wfe._add_event("DecisionTaskStarted")
    ids = [evt.event_id for evt in wfe.events()]
    assert ids == [1, 2, 3]


@freeze_time("2015-01-01 12:00:00")
def test_workflow_execution_start():
    wfe = make_workflow_execution()
    assert wfe.events() == []

    wfe.start()
    assert wfe.start_timestamp == 1420113600.0
    assert len(wfe.events()) == 2
    assert wfe.events()[0].event_type == "WorkflowExecutionStarted"
    assert wfe.events()[1].event_type == "DecisionTaskScheduled"


@freeze_time("2015-01-02 12:00:00")
def test_workflow_execution_complete():
    wfe = make_workflow_execution()
    wfe.complete(123, result="foo")

    assert wfe.execution_status == "CLOSED"
    assert wfe.close_status == "COMPLETED"
    assert wfe.close_timestamp == 1420200000.0
    assert wfe.events()[-1].event_type == "WorkflowExecutionCompleted"
    assert wfe.events()[-1].event_attributes["decisionTaskCompletedEventId"] == 123
    assert wfe.events()[-1].event_attributes["result"] == "foo"


@freeze_time("2015-01-02 12:00:00")
def test_workflow_execution_fail():
    wfe = make_workflow_execution()
    wfe.fail(123, details="some details", reason="my rules")

    assert wfe.execution_status == "CLOSED"
    assert wfe.close_status == "FAILED"
    assert wfe.close_timestamp == 1420200000.0
    assert wfe.events()[-1].event_type == "WorkflowExecutionFailed"
    assert wfe.events()[-1].event_attributes["decisionTaskCompletedEventId"] == 123
    assert wfe.events()[-1].event_attributes["details"] == "some details"
    assert wfe.events()[-1].event_attributes["reason"] == "my rules"


@freeze_time("2015-01-01 12:00:00")
def test_workflow_execution_schedule_activity_task():
    wfe = make_workflow_execution()
    assert wfe.latest_activity_task_timestamp is None

    wfe.schedule_activity_task(123, VALID_ACTIVITY_TASK_ATTRIBUTES)

    assert wfe.latest_activity_task_timestamp == 1420113600.0

    assert wfe.open_counts["openActivityTasks"] == 1
    last_event = wfe.events()[-1]
    assert last_event.event_type == "ActivityTaskScheduled"
    assert last_event.event_attributes["decisionTaskCompletedEventId"] == 123
    assert last_event.event_attributes["taskList"]["name"] == "task-list-name"

    assert len(wfe.activity_tasks) == 1
    task = wfe.activity_tasks[0]
    assert task.activity_id == "my-activity-001"
    assert task.activity_type.name == "test-activity"
    assert task in wfe.domain.activity_task_lists["task-list-name"]


def test_workflow_execution_schedule_activity_task_without_task_list_should_take_default():
    wfe = make_workflow_execution()
    wfe.domain.add_type(ActivityType("test-activity", "v1.2", task_list="foobar"))
    wfe.schedule_activity_task(
        123,
        {
            "activityId": "my-activity-001",
            "activityType": {"name": "test-activity", "version": "v1.2"},
            "scheduleToStartTimeout": "600",
            "scheduleToCloseTimeout": "600",
            "startToCloseTimeout": "600",
            "heartbeatTimeout": "300",
        },
    )

    assert wfe.open_counts["openActivityTasks"] == 1
    last_event = wfe.events()[-1]
    assert last_event.event_type == "ActivityTaskScheduled"
    assert last_event.event_attributes["taskList"]["name"] == "foobar"

    task = wfe.activity_tasks[0]
    assert task in wfe.domain.activity_task_lists["foobar"]


def test_workflow_execution_schedule_activity_task_should_fail_if_wrong_attributes():
    wfe = make_workflow_execution()
    at = ActivityType("test-activity", "v1.1")
    at.status = "DEPRECATED"
    wfe.domain.add_type(at)
    wfe.domain.add_type(ActivityType("test-activity", "v1.2"))

    hsh = {
        "activityId": "my-activity-001",
        "activityType": {"name": "test-activity-does-not-exists", "version": "v1.1"},
    }

    wfe.schedule_activity_task(123, hsh)
    last_event = wfe.events()[-1]
    assert last_event.event_type == "ScheduleActivityTaskFailed"
    assert last_event.event_attributes["cause"] == "ACTIVITY_TYPE_DOES_NOT_EXIST"

    hsh["activityType"]["name"] = "test-activity"
    wfe.schedule_activity_task(123, hsh)
    last_event = wfe.events()[-1]
    assert last_event.event_type == "ScheduleActivityTaskFailed"
    assert last_event.event_attributes["cause"] == "ACTIVITY_TYPE_DEPRECATED"

    hsh["activityType"]["version"] = "v1.2"
    wfe.schedule_activity_task(123, hsh)
    last_event = wfe.events()[-1]
    assert last_event.event_type == "ScheduleActivityTaskFailed"
    assert last_event.event_attributes["cause"] == "DEFAULT_TASK_LIST_UNDEFINED"

    hsh["taskList"] = {"name": "foobar"}
    wfe.schedule_activity_task(123, hsh)
    last_event = wfe.events()[-1]
    assert last_event.event_type == "ScheduleActivityTaskFailed"
    assert last_event.event_attributes["cause"] == (
        "DEFAULT_SCHEDULE_TO_START_TIMEOUT_UNDEFINED"
    )

    hsh["scheduleToStartTimeout"] = "600"
    wfe.schedule_activity_task(123, hsh)
    last_event = wfe.events()[-1]
    assert last_event.event_type == "ScheduleActivityTaskFailed"
    assert last_event.event_attributes["cause"] == (
        "DEFAULT_SCHEDULE_TO_CLOSE_TIMEOUT_UNDEFINED"
    )

    hsh["scheduleToCloseTimeout"] = "600"
    wfe.schedule_activity_task(123, hsh)
    last_event = wfe.events()[-1]
    assert last_event.event_type == "ScheduleActivityTaskFailed"
    assert last_event.event_attributes["cause"] == (
        "DEFAULT_START_TO_CLOSE_TIMEOUT_UNDEFINED"
    )

    hsh["startToCloseTimeout"] = "600"
    wfe.schedule_activity_task(123, hsh)
    last_event = wfe.events()[-1]
    assert last_event.event_type == "ScheduleActivityTaskFailed"
    assert last_event.event_attributes["cause"] == (
        "DEFAULT_HEARTBEAT_TIMEOUT_UNDEFINED"
    )

    assert wfe.open_counts["openActivityTasks"] == 0
    assert len(wfe.activity_tasks) == 0
    assert len(wfe.domain.activity_task_lists) == 0

    hsh["heartbeatTimeout"] = "300"
    wfe.schedule_activity_task(123, hsh)
    last_event = wfe.events()[-1]
    assert last_event.event_type == "ActivityTaskScheduled"

    task = wfe.activity_tasks[0]
    assert task in wfe.domain.activity_task_lists["foobar"]
    assert wfe.open_counts["openDecisionTasks"] == 0
    assert wfe.open_counts["openActivityTasks"] == 1


def test_workflow_execution_schedule_activity_task_failure_triggers_new_decision():
    wfe = make_workflow_execution()
    wfe.start()
    task_token = wfe.decision_tasks[-1].task_token
    wfe.start_decision_task(task_token)
    wfe.complete_decision_task(
        task_token,
        execution_context="free-form execution context",
        decisions=[
            {
                "decisionType": "ScheduleActivityTask",
                "scheduleActivityTaskDecisionAttributes": {
                    "activityId": "my-activity-001",
                    "activityType": {
                        "name": "test-activity-does-not-exist",
                        "version": "v1.2",
                    },
                },
            },
            {
                "decisionType": "ScheduleActivityTask",
                "scheduleActivityTaskDecisionAttributes": {
                    "activityId": "my-activity-001",
                    "activityType": {
                        "name": "test-activity-does-not-exist",
                        "version": "v1.2",
                    },
                },
            },
        ],
    )

    assert wfe.latest_execution_context == "free-form execution context"
    assert wfe.open_counts["openActivityTasks"] == 0
    assert wfe.open_counts["openDecisionTasks"] == 1
    last_events = wfe.events()[-3:]
    assert last_events[0].event_type == "ScheduleActivityTaskFailed"
    assert last_events[1].event_type == "ScheduleActivityTaskFailed"
    assert last_events[2].event_type == "DecisionTaskScheduled"


def test_workflow_execution_schedule_activity_task_with_same_activity_id():
    wfe = make_workflow_execution()

    wfe.schedule_activity_task(123, VALID_ACTIVITY_TASK_ATTRIBUTES)
    assert wfe.open_counts["openActivityTasks"] == 1
    last_event = wfe.events()[-1]
    assert last_event.event_type == "ActivityTaskScheduled"

    wfe.schedule_activity_task(123, VALID_ACTIVITY_TASK_ATTRIBUTES)
    assert wfe.open_counts["openActivityTasks"] == 1
    last_event = wfe.events()[-1]
    assert last_event.event_type == "ScheduleActivityTaskFailed"
    assert last_event.event_attributes["cause"] == "ACTIVITY_ID_ALREADY_IN_USE"


def test_workflow_execution_start_activity_task():
    wfe = make_workflow_execution()
    wfe.schedule_activity_task(123, VALID_ACTIVITY_TASK_ATTRIBUTES)
    task_token = wfe.activity_tasks[-1].task_token
    wfe.start_activity_task(task_token, identity="worker01")
    task = wfe.activity_tasks[-1]
    assert task.state == "STARTED"
    assert wfe.events()[-1].event_type == "ActivityTaskStarted"
    assert wfe.events()[-1].event_attributes["identity"] == "worker01"


def test_complete_activity_task():
    wfe = make_workflow_execution()
    wfe.schedule_activity_task(123, VALID_ACTIVITY_TASK_ATTRIBUTES)
    task_token = wfe.activity_tasks[-1].task_token

    assert wfe.open_counts["openActivityTasks"] == 1
    assert wfe.open_counts["openDecisionTasks"] == 0

    wfe.start_activity_task(task_token, identity="worker01")
    wfe.complete_activity_task(task_token, result="a superb result")

    task = wfe.activity_tasks[-1]
    assert task.state == "COMPLETED"
    assert wfe.events()[-2].event_type == "ActivityTaskCompleted"
    assert wfe.events()[-1].event_type == "DecisionTaskScheduled"

    assert wfe.open_counts["openActivityTasks"] == 0
    assert wfe.open_counts["openDecisionTasks"] == 1


def test_terminate():
    wfe = make_workflow_execution()
    wfe.schedule_decision_task()
    wfe.terminate()

    assert wfe.execution_status == "CLOSED"
    assert wfe.close_status == "TERMINATED"
    assert wfe.close_cause == "OPERATOR_INITIATED"
    assert wfe.open_counts["openDecisionTasks"] == 1

    last_event = wfe.events()[-1]
    assert last_event.event_type == "WorkflowExecutionTerminated"
    # take default child_policy if not provided (as here)
    assert last_event.event_attributes["childPolicy"] == "ABANDON"


def test_first_timeout():
    wfe = make_workflow_execution()
    assert wfe.first_timeout() is None

    with freeze_time("2015-01-01 12:00:00"):
        wfe.start()
        assert wfe.first_timeout() is None

    with freeze_time("2015-01-01 14:01"):
        # 2 hours timeout reached
        assert isinstance(wfe.first_timeout(), Timeout)


# See moto/swf/models/workflow_execution.py "_process_timeouts()" for more
# details
def test_timeouts_are_processed_in_order_and_reevaluated():
    # Let's make a Workflow Execution with the following properties:
    # - execution start to close timeout of 8 mins
    # - (decision) task start to close timeout of 5 mins
    #
    # Now start the workflow execution, and look at the history 15 mins later:
    # - a first decision task is fired just after workflow execution start
    # - the first decision task should have timed out after 5 mins
    # - that fires a new decision task (which we hack to start automatically)
    # - then the workflow timeouts after 8 mins (shows gradual reevaluation)
    # - but the last scheduled decision task should *not* timeout (workflow closed)
    with freeze_time("2015-01-01 12:00:00"):
        wfe = make_workflow_execution(
            execution_start_to_close_timeout=8 * 60, task_start_to_close_timeout=5 * 60
        )
        # decision will automatically start
        wfe = auto_start_decision_tasks(wfe)
        wfe.start()
        event_idx = len(wfe.events())

    with freeze_time("2015-01-01 12:08:00"):
        wfe._process_timeouts()

        event_types = [e.event_type for e in wfe.events()[event_idx:]]
        assert event_types == [
            "DecisionTaskTimedOut",
            "DecisionTaskScheduled",
            "DecisionTaskStarted",
            "WorkflowExecutionTimedOut",
        ]


def test_record_marker():
    wfe = make_workflow_execution()
    MARKER_EVENT_ATTRIBUTES = {"markerName": "example_marker"}

    wfe.record_marker(123, MARKER_EVENT_ATTRIBUTES)

    last_event = wfe.events()[-1]
    assert last_event.event_type == "MarkerRecorded"
    assert last_event.event_attributes["markerName"] == "example_marker"
    assert last_event.event_attributes["decisionTaskCompletedEventId"] == 123


def test_start_timer():
    wfe = make_workflow_execution()
    START_TIMER_EVENT_ATTRIBUTES = {"startToFireTimeout": "10", "timerId": "abc123"}
    with patch("moto.swf.models.workflow_execution.ThreadingTimer"):

        wfe.start_timer(123, START_TIMER_EVENT_ATTRIBUTES)

        last_event = wfe.events()[-1]
        assert last_event.event_type == "TimerStarted"
        assert last_event.event_attributes["startToFireTimeout"] == "10"
        assert last_event.event_attributes["timerId"] == "abc123"
        assert last_event.event_attributes["decisionTaskCompletedEventId"] == 123


def test_start_timer_correctly_fires_timer_later():
    wfe = make_workflow_execution()
    START_TIMER_EVENT_ATTRIBUTES = {"startToFireTimeout": "60", "timerId": "abc123"}

    # Patch thread's event with one that immediately resolves
    with patch("threading.Event.wait"):
        wfe.start_timer(123, START_TIMER_EVENT_ATTRIBUTES)
        # Small wait to let both events populate
        sleep(0.5)

        second_to_last_event = wfe.events()[-2]
        last_event = wfe.events()[-1]
        assert second_to_last_event.event_type == "TimerFired"
        assert second_to_last_event.event_attributes["timerId"] == "abc123"
        assert second_to_last_event.event_attributes["startedEventId"] == 1
        assert last_event.event_type == "DecisionTaskScheduled"


def test_start_timer_fails_if_timer_already_started():
    wfe = make_workflow_execution()
    existing_timer = Mock(spec=ThreadingTimer)
    existing_timer.is_alive.return_value = True
    wfe._timers["abc123"] = Timer(existing_timer, 1)
    START_TIMER_EVENT_ATTRIBUTES = {"startToFireTimeout": "10", "timerId": "abc123"}

    wfe.start_timer(123, START_TIMER_EVENT_ATTRIBUTES)

    last_event = wfe.events()[-1]
    assert last_event.event_type == "StartTimerFailed"
    assert last_event.event_attributes["cause"] == "TIMER_ID_ALREADY_IN_USE"
    assert last_event.event_attributes["timerId"] == "abc123"
    assert last_event.event_attributes["decisionTaskCompletedEventId"] == 123


def test_cancel_timer():
    wfe = make_workflow_execution()
    existing_timer = Mock(spec=ThreadingTimer)
    existing_timer.is_alive.return_value = True
    wfe._timers["abc123"] = Timer(existing_timer, 1)

    wfe.cancel_timer(123, "abc123")

    last_event = wfe.events()[-1]
    assert last_event.event_type == "TimerCancelled"
    assert last_event.event_attributes["startedEventId"] == 1
    assert last_event.event_attributes["timerId"] == "abc123"
    assert last_event.event_attributes["decisionTaskCompletedEventId"] == 123
    existing_timer.cancel.assert_called_once()
    assert not wfe._timers.get("abc123")


def test_cancel_timer_fails_if_timer_not_found():
    wfe = make_workflow_execution()

    wfe.cancel_timer(123, "abc123")

    last_event = wfe.events()[-1]
    assert last_event.event_type == "CancelTimerFailed"
    assert last_event.event_attributes["cause"] == "TIMER_ID_UNKNOWN"
    assert last_event.event_attributes["decisionTaskCompletedEventId"] == 123


def test_cancel_workflow():
    wfe = make_workflow_execution()
    wfe.open_counts["openDecisionTasks"] = 1

    wfe.cancel(123, "I want to cancel")

    last_event = wfe.events()[-1]
    assert last_event.event_type == "WorkflowExecutionCanceled"
    assert last_event.event_attributes["details"] == "I want to cancel"
    assert last_event.event_attributes["decisionTaskCompletedEventId"] == 123


def test_cancel_workflow_fails_if_open_decision():
    wfe = make_workflow_execution()
    wfe.open_counts["openDecisionTasks"] = 2

    wfe.cancel(123, "I want to cancel")

    last_event = wfe.events()[-1]
    assert last_event.event_type == "CancelWorkflowExecutionFailed"
    assert last_event.event_attributes["cause"] == "UNHANDLED_DECISION"
    assert last_event.event_attributes["decisionTaskCompletedEventId"] == 123
