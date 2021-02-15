from boto.swf.exceptions import SWFResponseError
from freezegun import freeze_time
import sure  # noqa

from moto import mock_swf_deprecated
from moto.swf import swf_backend

from ..utils import setup_workflow, SCHEDULE_ACTIVITY_TASK_DECISION


# PollForActivityTask endpoint
@mock_swf_deprecated
def test_poll_for_activity_task_when_one():
    conn = setup_workflow()
    decision_token = conn.poll_for_decision_task("test-domain", "queue")["taskToken"]
    conn.respond_decision_task_completed(
        decision_token, decisions=[SCHEDULE_ACTIVITY_TASK_DECISION]
    )
    resp = conn.poll_for_activity_task(
        "test-domain", "activity-task-list", identity="surprise"
    )
    resp["activityId"].should.equal("my-activity-001")
    resp["taskToken"].should_not.be.none

    resp = conn.get_workflow_execution_history(
        "test-domain", conn.run_id, "uid-abcd1234"
    )
    resp["events"][-1]["eventType"].should.equal("ActivityTaskStarted")
    resp["events"][-1]["activityTaskStartedEventAttributes"].should.equal(
        {"identity": "surprise", "scheduledEventId": 5}
    )


@mock_swf_deprecated
def test_poll_for_activity_task_when_none():
    conn = setup_workflow()
    resp = conn.poll_for_activity_task("test-domain", "activity-task-list")
    resp.should.equal({"startedEventId": 0})


@mock_swf_deprecated
def test_poll_for_activity_task_on_non_existent_queue():
    conn = setup_workflow()
    resp = conn.poll_for_activity_task("test-domain", "non-existent-queue")
    resp.should.equal({"startedEventId": 0})


# CountPendingActivityTasks endpoint
@mock_swf_deprecated
def test_count_pending_activity_tasks():
    conn = setup_workflow()
    decision_token = conn.poll_for_decision_task("test-domain", "queue")["taskToken"]
    conn.respond_decision_task_completed(
        decision_token, decisions=[SCHEDULE_ACTIVITY_TASK_DECISION]
    )

    resp = conn.count_pending_activity_tasks("test-domain", "activity-task-list")
    resp.should.equal({"count": 1, "truncated": False})


@mock_swf_deprecated
def test_count_pending_decision_tasks_on_non_existent_task_list():
    conn = setup_workflow()
    resp = conn.count_pending_activity_tasks("test-domain", "non-existent")
    resp.should.equal({"count": 0, "truncated": False})


# RespondActivityTaskCompleted endpoint
@mock_swf_deprecated
def test_respond_activity_task_completed():
    conn = setup_workflow()
    decision_token = conn.poll_for_decision_task("test-domain", "queue")["taskToken"]
    conn.respond_decision_task_completed(
        decision_token, decisions=[SCHEDULE_ACTIVITY_TASK_DECISION]
    )
    activity_token = conn.poll_for_activity_task("test-domain", "activity-task-list")[
        "taskToken"
    ]

    resp = conn.respond_activity_task_completed(
        activity_token, result="result of the task"
    )
    resp.should.be.none

    resp = conn.get_workflow_execution_history(
        "test-domain", conn.run_id, "uid-abcd1234"
    )
    resp["events"][-2]["eventType"].should.equal("ActivityTaskCompleted")
    resp["events"][-2]["activityTaskCompletedEventAttributes"].should.equal(
        {"result": "result of the task", "scheduledEventId": 5, "startedEventId": 6}
    )


@mock_swf_deprecated
def test_respond_activity_task_completed_on_closed_workflow_execution():
    conn = setup_workflow()
    decision_token = conn.poll_for_decision_task("test-domain", "queue")["taskToken"]
    conn.respond_decision_task_completed(
        decision_token, decisions=[SCHEDULE_ACTIVITY_TASK_DECISION]
    )
    activity_token = conn.poll_for_activity_task("test-domain", "activity-task-list")[
        "taskToken"
    ]

    # bad: we're closing workflow execution manually, but endpoints are not
    # coded for now..
    wfe = swf_backend.domains[0].workflow_executions[-1]
    wfe.execution_status = "CLOSED"
    # /bad

    conn.respond_activity_task_completed.when.called_with(activity_token).should.throw(
        SWFResponseError, "WorkflowExecution="
    )


@mock_swf_deprecated
def test_respond_activity_task_completed_with_task_already_completed():
    conn = setup_workflow()
    decision_token = conn.poll_for_decision_task("test-domain", "queue")["taskToken"]
    conn.respond_decision_task_completed(
        decision_token, decisions=[SCHEDULE_ACTIVITY_TASK_DECISION]
    )
    activity_token = conn.poll_for_activity_task("test-domain", "activity-task-list")[
        "taskToken"
    ]

    conn.respond_activity_task_completed(activity_token)

    conn.respond_activity_task_completed.when.called_with(activity_token).should.throw(
        SWFResponseError, "Unknown activity, scheduledEventId = 5"
    )


# RespondActivityTaskFailed endpoint
@mock_swf_deprecated
def test_respond_activity_task_failed():
    conn = setup_workflow()
    decision_token = conn.poll_for_decision_task("test-domain", "queue")["taskToken"]
    conn.respond_decision_task_completed(
        decision_token, decisions=[SCHEDULE_ACTIVITY_TASK_DECISION]
    )
    activity_token = conn.poll_for_activity_task("test-domain", "activity-task-list")[
        "taskToken"
    ]

    resp = conn.respond_activity_task_failed(
        activity_token, reason="short reason", details="long details"
    )
    resp.should.be.none

    resp = conn.get_workflow_execution_history(
        "test-domain", conn.run_id, "uid-abcd1234"
    )
    resp["events"][-2]["eventType"].should.equal("ActivityTaskFailed")
    resp["events"][-2]["activityTaskFailedEventAttributes"].should.equal(
        {
            "reason": "short reason",
            "details": "long details",
            "scheduledEventId": 5,
            "startedEventId": 6,
        }
    )


@mock_swf_deprecated
def test_respond_activity_task_completed_with_wrong_token():
    # NB: we just test ONE failure case for RespondActivityTaskFailed
    # because the safeguards are shared with RespondActivityTaskCompleted, so
    # no need to retest everything end-to-end.
    conn = setup_workflow()
    decision_token = conn.poll_for_decision_task("test-domain", "queue")["taskToken"]
    conn.respond_decision_task_completed(
        decision_token, decisions=[SCHEDULE_ACTIVITY_TASK_DECISION]
    )
    conn.poll_for_activity_task("test-domain", "activity-task-list")
    conn.respond_activity_task_failed.when.called_with(
        "not-a-correct-token"
    ).should.throw(SWFResponseError, "Invalid token")


# RecordActivityTaskHeartbeat endpoint
@mock_swf_deprecated
def test_record_activity_task_heartbeat():
    conn = setup_workflow()
    decision_token = conn.poll_for_decision_task("test-domain", "queue")["taskToken"]
    conn.respond_decision_task_completed(
        decision_token, decisions=[SCHEDULE_ACTIVITY_TASK_DECISION]
    )
    activity_token = conn.poll_for_activity_task("test-domain", "activity-task-list")[
        "taskToken"
    ]

    resp = conn.record_activity_task_heartbeat(activity_token)
    resp.should.equal({"cancelRequested": False})


@mock_swf_deprecated
def test_record_activity_task_heartbeat_with_wrong_token():
    conn = setup_workflow()
    decision_token = conn.poll_for_decision_task("test-domain", "queue")["taskToken"]
    conn.respond_decision_task_completed(
        decision_token, decisions=[SCHEDULE_ACTIVITY_TASK_DECISION]
    )
    conn.poll_for_activity_task("test-domain", "activity-task-list")["taskToken"]

    conn.record_activity_task_heartbeat.when.called_with(
        "bad-token", details="some progress details"
    ).should.throw(SWFResponseError)


@mock_swf_deprecated
def test_record_activity_task_heartbeat_sets_details_in_case_of_timeout():
    conn = setup_workflow()
    decision_token = conn.poll_for_decision_task("test-domain", "queue")["taskToken"]
    conn.respond_decision_task_completed(
        decision_token, decisions=[SCHEDULE_ACTIVITY_TASK_DECISION]
    )
    with freeze_time("2015-01-01 12:00:00"):
        activity_token = conn.poll_for_activity_task(
            "test-domain", "activity-task-list"
        )["taskToken"]
        conn.record_activity_task_heartbeat(
            activity_token, details="some progress details"
        )

    with freeze_time("2015-01-01 12:05:30"):
        # => Activity Task Heartbeat timeout reached!!
        resp = conn.get_workflow_execution_history(
            "test-domain", conn.run_id, "uid-abcd1234"
        )
        resp["events"][-2]["eventType"].should.equal("ActivityTaskTimedOut")
        attrs = resp["events"][-2]["activityTaskTimedOutEventAttributes"]
        attrs["details"].should.equal("some progress details")
