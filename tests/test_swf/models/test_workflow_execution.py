from freezegun import freeze_time
import sure  # noqa

from moto.swf.models import (
    ActivityType,
    Timeout,
    WorkflowType,
    WorkflowExecution,
)
from moto.swf.exceptions import SWFDefaultUndefinedFault
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

    wfe.domain.should.equal(domain)
    wfe.workflow_type.should.equal(wft)
    wfe.child_policy.should.equal("TERMINATE")


def test_workflow_execution_creation_child_policy_logic():
    domain = get_basic_domain()

    WorkflowExecution(
        domain,
        WorkflowType(
            "test-workflow", "v1.0",
            task_list="queue", default_child_policy="ABANDON",
            default_execution_start_to_close_timeout="300",
            default_task_start_to_close_timeout="300",
        ),
        "ab1234"
    ).child_policy.should.equal("ABANDON")

    WorkflowExecution(
        domain,
        WorkflowType(
            "test-workflow", "v1.0", task_list="queue",
            default_execution_start_to_close_timeout="300",
            default_task_start_to_close_timeout="300",
        ),
        "ab1234",
        child_policy="REQUEST_CANCEL"
    ).child_policy.should.equal("REQUEST_CANCEL")

    WorkflowExecution.when.called_with(
        domain,
        WorkflowType("test-workflow", "v1.0"), "ab1234"
    ).should.throw(SWFDefaultUndefinedFault)


def test_workflow_execution_string_representation():
    wfe = make_workflow_execution(child_policy="TERMINATE")
    str(wfe).should.match(r"^WorkflowExecution\(run_id: .*\)")


def test_workflow_execution_generates_a_random_run_id():
    domain = get_basic_domain()
    wft = get_basic_workflow_type()
    wfe1 = WorkflowExecution(domain, wft, "ab1234", child_policy="TERMINATE")
    wfe2 = WorkflowExecution(domain, wft, "ab1235", child_policy="TERMINATE")
    wfe1.run_id.should_not.equal(wfe2.run_id)


def test_workflow_execution_short_dict_representation():
    domain = get_basic_domain()
    wf_type = WorkflowType(
        "test-workflow", "v1.0",
        task_list="queue", default_child_policy="ABANDON",
        default_execution_start_to_close_timeout="300",
        default_task_start_to_close_timeout="300",
    )
    wfe = WorkflowExecution(domain, wf_type, "ab1234")

    sd = wfe.to_short_dict()
    sd["workflowId"].should.equal("ab1234")
    sd.should.contain("runId")


def test_workflow_execution_medium_dict_representation():
    domain = get_basic_domain()
    wf_type = WorkflowType(
        "test-workflow", "v1.0",
        task_list="queue", default_child_policy="ABANDON",
        default_execution_start_to_close_timeout="300",
        default_task_start_to_close_timeout="300",
    )
    wfe = WorkflowExecution(domain, wf_type, "ab1234")

    md = wfe.to_medium_dict()
    md["execution"].should.equal(wfe.to_short_dict())
    md["workflowType"].should.equal(wf_type.to_short_dict())
    md["startTimestamp"].should.be.a('float')
    md["executionStatus"].should.equal("OPEN")
    md["cancelRequested"].should.be.falsy
    md.should_not.contain("tagList")

    wfe.tag_list = ["foo", "bar", "baz"]
    md = wfe.to_medium_dict()
    md["tagList"].should.equal(["foo", "bar", "baz"])


def test_workflow_execution_full_dict_representation():
    domain = get_basic_domain()
    wf_type = WorkflowType(
        "test-workflow", "v1.0",
        task_list="queue", default_child_policy="ABANDON",
        default_execution_start_to_close_timeout="300",
        default_task_start_to_close_timeout="300",
    )
    wfe = WorkflowExecution(domain, wf_type, "ab1234")

    fd = wfe.to_full_dict()
    fd["executionInfo"].should.equal(wfe.to_medium_dict())
    fd["openCounts"]["openTimers"].should.equal(0)
    fd["openCounts"]["openDecisionTasks"].should.equal(0)
    fd["openCounts"]["openActivityTasks"].should.equal(0)
    fd["executionConfiguration"].should.equal({
        "childPolicy": "ABANDON",
        "executionStartToCloseTimeout": "300",
        "taskList": {"name": "queue"},
        "taskStartToCloseTimeout": "300",
    })


def test_workflow_execution_list_dict_representation():
    domain = get_basic_domain()
    wf_type = WorkflowType(
        'test-workflow', 'v1.0',
        task_list='queue', default_child_policy='ABANDON',
        default_execution_start_to_close_timeout='300',
        default_task_start_to_close_timeout='300',
    )
    wfe = WorkflowExecution(domain, wf_type, 'ab1234')

    ld = wfe.to_list_dict()
    ld['workflowType']['version'].should.equal('v1.0')
    ld['workflowType']['name'].should.equal('test-workflow')
    ld['executionStatus'].should.equal('OPEN')
    ld['execution']['workflowId'].should.equal('ab1234')
    ld['execution'].should.contain('runId')
    ld['cancelRequested'].should.be.false
    ld.should.contain('startTimestamp')


def test_workflow_execution_schedule_decision_task():
    wfe = make_workflow_execution()
    wfe.open_counts["openDecisionTasks"].should.equal(0)
    wfe.schedule_decision_task()
    wfe.open_counts["openDecisionTasks"].should.equal(1)


def test_workflow_execution_start_decision_task():
    wfe = make_workflow_execution()
    wfe.schedule_decision_task()
    dt = wfe.decision_tasks[0]
    wfe.start_decision_task(dt.task_token, identity="srv01")
    dt = wfe.decision_tasks[0]
    dt.state.should.equal("STARTED")
    wfe.events()[-1].event_type.should.equal("DecisionTaskStarted")
    wfe.events()[-1].event_attributes["identity"].should.equal("srv01")


def test_workflow_execution_history_events_ids():
    wfe = make_workflow_execution()
    wfe._add_event("WorkflowExecutionStarted")
    wfe._add_event("DecisionTaskScheduled")
    wfe._add_event("DecisionTaskStarted")
    ids = [evt.event_id for evt in wfe.events()]
    ids.should.equal([1, 2, 3])


@freeze_time("2015-01-01 12:00:00")
def test_workflow_execution_start():
    wfe = make_workflow_execution()
    wfe.events().should.equal([])

    wfe.start()
    wfe.start_timestamp.should.equal(1420113600.0)
    wfe.events().should.have.length_of(2)
    wfe.events()[0].event_type.should.equal("WorkflowExecutionStarted")
    wfe.events()[1].event_type.should.equal("DecisionTaskScheduled")


@freeze_time("2015-01-02 12:00:00")
def test_workflow_execution_complete():
    wfe = make_workflow_execution()
    wfe.complete(123, result="foo")

    wfe.execution_status.should.equal("CLOSED")
    wfe.close_status.should.equal("COMPLETED")
    wfe.close_timestamp.should.equal(1420200000.0)
    wfe.events()[-1].event_type.should.equal("WorkflowExecutionCompleted")
    wfe.events()[-1].event_attributes["decisionTaskCompletedEventId"].should.equal(123)
    wfe.events()[-1].event_attributes["result"].should.equal("foo")


@freeze_time("2015-01-02 12:00:00")
def test_workflow_execution_fail():
    wfe = make_workflow_execution()
    wfe.fail(123, details="some details", reason="my rules")

    wfe.execution_status.should.equal("CLOSED")
    wfe.close_status.should.equal("FAILED")
    wfe.close_timestamp.should.equal(1420200000.0)
    wfe.events()[-1].event_type.should.equal("WorkflowExecutionFailed")
    wfe.events()[-1].event_attributes["decisionTaskCompletedEventId"].should.equal(123)
    wfe.events()[-1].event_attributes["details"].should.equal("some details")
    wfe.events()[-1].event_attributes["reason"].should.equal("my rules")


@freeze_time("2015-01-01 12:00:00")
def test_workflow_execution_schedule_activity_task():
    wfe = make_workflow_execution()
    wfe.latest_activity_task_timestamp.should.be.none

    wfe.schedule_activity_task(123, VALID_ACTIVITY_TASK_ATTRIBUTES)

    wfe.latest_activity_task_timestamp.should.equal(1420113600.0)

    wfe.open_counts["openActivityTasks"].should.equal(1)
    last_event = wfe.events()[-1]
    last_event.event_type.should.equal("ActivityTaskScheduled")
    last_event.event_attributes[
        "decisionTaskCompletedEventId"].should.equal(123)
    last_event.event_attributes["taskList"][
        "name"].should.equal("task-list-name")

    wfe.activity_tasks.should.have.length_of(1)
    task = wfe.activity_tasks[0]
    task.activity_id.should.equal("my-activity-001")
    task.activity_type.name.should.equal("test-activity")
    wfe.domain.activity_task_lists["task-list-name"].should.contain(task)


def test_workflow_execution_schedule_activity_task_without_task_list_should_take_default():
    wfe = make_workflow_execution()
    wfe.domain.add_type(
        ActivityType("test-activity", "v1.2", task_list="foobar")
    )
    wfe.schedule_activity_task(123, {
        "activityId": "my-activity-001",
        "activityType": {"name": "test-activity", "version": "v1.2"},
        "scheduleToStartTimeout": "600",
        "scheduleToCloseTimeout": "600",
        "startToCloseTimeout": "600",
        "heartbeatTimeout": "300",
    })

    wfe.open_counts["openActivityTasks"].should.equal(1)
    last_event = wfe.events()[-1]
    last_event.event_type.should.equal("ActivityTaskScheduled")
    last_event.event_attributes["taskList"]["name"].should.equal("foobar")

    task = wfe.activity_tasks[0]
    wfe.domain.activity_task_lists["foobar"].should.contain(task)


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
    last_event.event_type.should.equal("ScheduleActivityTaskFailed")
    last_event.event_attributes["cause"].should.equal(
        "ACTIVITY_TYPE_DOES_NOT_EXIST")

    hsh["activityType"]["name"] = "test-activity"
    wfe.schedule_activity_task(123, hsh)
    last_event = wfe.events()[-1]
    last_event.event_type.should.equal("ScheduleActivityTaskFailed")
    last_event.event_attributes["cause"].should.equal(
        "ACTIVITY_TYPE_DEPRECATED")

    hsh["activityType"]["version"] = "v1.2"
    wfe.schedule_activity_task(123, hsh)
    last_event = wfe.events()[-1]
    last_event.event_type.should.equal("ScheduleActivityTaskFailed")
    last_event.event_attributes["cause"].should.equal(
        "DEFAULT_TASK_LIST_UNDEFINED")

    hsh["taskList"] = {"name": "foobar"}
    wfe.schedule_activity_task(123, hsh)
    last_event = wfe.events()[-1]
    last_event.event_type.should.equal("ScheduleActivityTaskFailed")
    last_event.event_attributes["cause"].should.equal(
        "DEFAULT_SCHEDULE_TO_START_TIMEOUT_UNDEFINED")

    hsh["scheduleToStartTimeout"] = "600"
    wfe.schedule_activity_task(123, hsh)
    last_event = wfe.events()[-1]
    last_event.event_type.should.equal("ScheduleActivityTaskFailed")
    last_event.event_attributes["cause"].should.equal(
        "DEFAULT_SCHEDULE_TO_CLOSE_TIMEOUT_UNDEFINED")

    hsh["scheduleToCloseTimeout"] = "600"
    wfe.schedule_activity_task(123, hsh)
    last_event = wfe.events()[-1]
    last_event.event_type.should.equal("ScheduleActivityTaskFailed")
    last_event.event_attributes["cause"].should.equal(
        "DEFAULT_START_TO_CLOSE_TIMEOUT_UNDEFINED")

    hsh["startToCloseTimeout"] = "600"
    wfe.schedule_activity_task(123, hsh)
    last_event = wfe.events()[-1]
    last_event.event_type.should.equal("ScheduleActivityTaskFailed")
    last_event.event_attributes["cause"].should.equal(
        "DEFAULT_HEARTBEAT_TIMEOUT_UNDEFINED")

    wfe.open_counts["openActivityTasks"].should.equal(0)
    wfe.activity_tasks.should.have.length_of(0)
    wfe.domain.activity_task_lists.should.have.length_of(0)

    hsh["heartbeatTimeout"] = "300"
    wfe.schedule_activity_task(123, hsh)
    last_event = wfe.events()[-1]
    last_event.event_type.should.equal("ActivityTaskScheduled")

    task = wfe.activity_tasks[0]
    wfe.domain.activity_task_lists["foobar"].should.contain(task)
    wfe.open_counts["openDecisionTasks"].should.equal(0)
    wfe.open_counts["openActivityTasks"].should.equal(1)


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
                        "version": "v1.2"
                    },
                }
            },
            {
                "decisionType": "ScheduleActivityTask",
                "scheduleActivityTaskDecisionAttributes": {
                    "activityId": "my-activity-001",
                    "activityType": {
                        "name": "test-activity-does-not-exist",
                        "version": "v1.2"
                    },
                }
            },
        ])

    wfe.latest_execution_context.should.equal("free-form execution context")
    wfe.open_counts["openActivityTasks"].should.equal(0)
    wfe.open_counts["openDecisionTasks"].should.equal(1)
    last_events = wfe.events()[-3:]
    last_events[0].event_type.should.equal("ScheduleActivityTaskFailed")
    last_events[1].event_type.should.equal("ScheduleActivityTaskFailed")
    last_events[2].event_type.should.equal("DecisionTaskScheduled")


def test_workflow_execution_schedule_activity_task_with_same_activity_id():
    wfe = make_workflow_execution()

    wfe.schedule_activity_task(123, VALID_ACTIVITY_TASK_ATTRIBUTES)
    wfe.open_counts["openActivityTasks"].should.equal(1)
    last_event = wfe.events()[-1]
    last_event.event_type.should.equal("ActivityTaskScheduled")

    wfe.schedule_activity_task(123, VALID_ACTIVITY_TASK_ATTRIBUTES)
    wfe.open_counts["openActivityTasks"].should.equal(1)
    last_event = wfe.events()[-1]
    last_event.event_type.should.equal("ScheduleActivityTaskFailed")
    last_event.event_attributes["cause"].should.equal(
        "ACTIVITY_ID_ALREADY_IN_USE")


def test_workflow_execution_start_activity_task():
    wfe = make_workflow_execution()
    wfe.schedule_activity_task(123, VALID_ACTIVITY_TASK_ATTRIBUTES)
    task_token = wfe.activity_tasks[-1].task_token
    wfe.start_activity_task(task_token, identity="worker01")
    task = wfe.activity_tasks[-1]
    task.state.should.equal("STARTED")
    wfe.events()[-1].event_type.should.equal("ActivityTaskStarted")
    wfe.events()[-1].event_attributes["identity"].should.equal("worker01")


def test_complete_activity_task():
    wfe = make_workflow_execution()
    wfe.schedule_activity_task(123, VALID_ACTIVITY_TASK_ATTRIBUTES)
    task_token = wfe.activity_tasks[-1].task_token

    wfe.open_counts["openActivityTasks"].should.equal(1)
    wfe.open_counts["openDecisionTasks"].should.equal(0)

    wfe.start_activity_task(task_token, identity="worker01")
    wfe.complete_activity_task(task_token, result="a superb result")

    task = wfe.activity_tasks[-1]
    task.state.should.equal("COMPLETED")
    wfe.events()[-2].event_type.should.equal("ActivityTaskCompleted")
    wfe.events()[-1].event_type.should.equal("DecisionTaskScheduled")

    wfe.open_counts["openActivityTasks"].should.equal(0)
    wfe.open_counts["openDecisionTasks"].should.equal(1)


def test_terminate():
    wfe = make_workflow_execution()
    wfe.schedule_decision_task()
    wfe.terminate()

    wfe.execution_status.should.equal("CLOSED")
    wfe.close_status.should.equal("TERMINATED")
    wfe.close_cause.should.equal("OPERATOR_INITIATED")
    wfe.open_counts["openDecisionTasks"].should.equal(1)

    last_event = wfe.events()[-1]
    last_event.event_type.should.equal("WorkflowExecutionTerminated")
    # take default child_policy if not provided (as here)
    last_event.event_attributes["childPolicy"].should.equal("ABANDON")


def test_first_timeout():
    wfe = make_workflow_execution()
    wfe.first_timeout().should.be.none

    with freeze_time("2015-01-01 12:00:00"):
        wfe.start()
        wfe.first_timeout().should.be.none

    with freeze_time("2015-01-01 14:01"):
        # 2 hours timeout reached
        wfe.first_timeout().should.be.a(Timeout)


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
            execution_start_to_close_timeout=8 * 60,
            task_start_to_close_timeout=5 * 60,
        )
        # decision will automatically start
        wfe = auto_start_decision_tasks(wfe)
        wfe.start()
        event_idx = len(wfe.events())

    with freeze_time("2015-01-01 12:08:00"):
        wfe._process_timeouts()

        event_types = [e.event_type for e in wfe.events()[event_idx:]]
        event_types.should.equal([
            "DecisionTaskTimedOut",
            "DecisionTaskScheduled",
            "DecisionTaskStarted",
            "WorkflowExecutionTimedOut",
        ])
