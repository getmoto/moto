from sure import expect
from freezegun import freeze_time

from moto.swf.models import (
    DecisionTask,
    Domain,
    GenericType,
    HistoryEvent,
    WorkflowType,
    WorkflowExecution,
)
from moto.swf.exceptions import (
    SWFDefaultUndefinedFault,
)

from .utils import get_basic_workflow_type


# Domain
def test_domain_short_dict_representation():
    domain = Domain("foo", "52")
    domain.to_short_dict().should.equal({"name":"foo", "status":"REGISTERED"})

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


# GenericType (ActivityType, WorkflowType)
class FooType(GenericType):
    @property
    def kind(self):
        return "foo"

    @property
    def _configuration_keys(self):
        return ["justAnExampleTimeout"]


def test_type_short_dict_representation():
    _type = FooType("test-foo", "v1.0")
    _type.to_short_dict().should.equal({"name": "test-foo", "version": "v1.0"})

def test_type_medium_dict_representation():
    _type = FooType("test-foo", "v1.0")
    _type.to_medium_dict()["fooType"].should.equal(_type.to_short_dict())
    _type.to_medium_dict()["status"].should.equal("REGISTERED")
    _type.to_medium_dict().should.contain("creationDate")
    _type.to_medium_dict().should_not.contain("deprecationDate")
    _type.to_medium_dict().should_not.contain("description")

    _type.description = "foo bar"
    _type.to_medium_dict()["description"].should.equal("foo bar")

    _type.status = "DEPRECATED"
    _type.to_medium_dict().should.contain("deprecationDate")

def test_type_full_dict_representation():
    _type = FooType("test-foo", "v1.0")
    _type.to_full_dict()["typeInfo"].should.equal(_type.to_medium_dict())
    _type.to_full_dict()["configuration"].should.equal({})

    _type.task_list = "foo"
    _type.to_full_dict()["configuration"]["defaultTaskList"].should.equal({"name":"foo"})

    _type.just_an_example_timeout = "60"
    _type.to_full_dict()["configuration"]["justAnExampleTimeout"].should.equal("60")

    _type.non_whitelisted_property = "34"
    _type.to_full_dict()["configuration"].keys().should.equal(["defaultTaskList", "justAnExampleTimeout"])

def test_type_string_representation():
    _type = FooType("test-foo", "v1.0")
    str(_type).should.equal("FooType(name: test-foo, version: v1.0, status: REGISTERED)")


# WorkflowExecution
def test_workflow_execution_creation():
    wft = get_basic_workflow_type()
    wfe = WorkflowExecution(wft, "ab1234", child_policy="TERMINATE")
    wfe.workflow_type.should.equal(wft)
    wfe.child_policy.should.equal("TERMINATE")

def test_workflow_execution_creation_child_policy_logic():
    WorkflowExecution(
        WorkflowType(
            "test-workflow", "v1.0",
            task_list="queue", default_child_policy="ABANDON",
            default_execution_start_to_close_timeout="300",
            default_task_start_to_close_timeout="300",
        ),
        "ab1234"
    ).child_policy.should.equal("ABANDON")

    WorkflowExecution(
        WorkflowType(
            "test-workflow", "v1.0", task_list="queue",
            default_execution_start_to_close_timeout="300",
            default_task_start_to_close_timeout="300",
        ),
        "ab1234",
        child_policy="REQUEST_CANCEL"
    ).child_policy.should.equal("REQUEST_CANCEL")

    WorkflowExecution.when.called_with(
        WorkflowType("test-workflow", "v1.0"), "ab1234"
    ).should.throw(SWFDefaultUndefinedFault)

def test_workflow_execution_string_representation():
    wft = get_basic_workflow_type()
    wfe = WorkflowExecution(wft, "ab1234", child_policy="TERMINATE")
    str(wfe).should.match(r"^WorkflowExecution\(run_id: .*\)")

def test_workflow_execution_generates_a_random_run_id():
    wft = get_basic_workflow_type()
    wfe1 = WorkflowExecution(wft, "ab1234", child_policy="TERMINATE")
    wfe2 = WorkflowExecution(wft, "ab1235", child_policy="TERMINATE")
    wfe1.run_id.should_not.equal(wfe2.run_id)

def test_workflow_execution_short_dict_representation():
    wf_type = WorkflowType(
        "test-workflow", "v1.0",
        task_list="queue", default_child_policy="ABANDON",
        default_execution_start_to_close_timeout="300",
        default_task_start_to_close_timeout="300",
    )
    wfe = WorkflowExecution(wf_type, "ab1234")

    sd = wfe.to_short_dict()
    sd["workflowId"].should.equal("ab1234")
    sd.should.contain("runId")

def test_workflow_execution_medium_dict_representation():
    wf_type = WorkflowType(
        "test-workflow", "v1.0",
        task_list="queue", default_child_policy="ABANDON",
        default_execution_start_to_close_timeout="300",
        default_task_start_to_close_timeout="300",
    )
    wfe = WorkflowExecution(wf_type, "ab1234")

    md = wfe.to_medium_dict()
    md["execution"].should.equal(wfe.to_short_dict())
    md["workflowType"].should.equal(wf_type.to_short_dict())
    md["startTimestamp"].should.be.a('float')
    md["executionStatus"].should.equal("OPEN")
    md["cancelRequested"].should.equal(False)
    md.should_not.contain("tagList")

    wfe.tag_list = ["foo", "bar", "baz"]
    md = wfe.to_medium_dict()
    md["tagList"].should.equal(["foo", "bar", "baz"])

def test_workflow_execution_full_dict_representation():
    wf_type = WorkflowType(
        "test-workflow", "v1.0",
        task_list="queue", default_child_policy="ABANDON",
        default_execution_start_to_close_timeout="300",
        default_task_start_to_close_timeout="300",
    )
    wfe = WorkflowExecution(wf_type, "ab1234")

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

def test_workflow_execution_schedule_decision_task():
    wft = get_basic_workflow_type()
    wfe = WorkflowExecution(wft, "ab1234")
    wfe.open_counts["openDecisionTasks"].should.equal(0)
    wfe.schedule_decision_task()
    wfe.open_counts["openDecisionTasks"].should.equal(1)

def test_workflow_execution_start_decision_task():
    wft = get_basic_workflow_type()
    wfe = WorkflowExecution(wft, "ab1234")
    wfe.schedule_decision_task()
    dt = wfe.decision_tasks[0]
    wfe.start_decision_task(dt.task_token, identity="srv01")
    dt = wfe.decision_tasks[0]
    dt.state.should.equal("STARTED")
    wfe.events[-1].event_type.should.equal("DecisionTaskStarted")
    wfe.events[-1].identity.should.equal("srv01")


# HistoryEvent
@freeze_time("2015-01-01 12:00:00")
def test_history_event_creation():
    he = HistoryEvent(123, "DecisionTaskStarted", scheduled_event_id=2)
    he.event_id.should.equal(123)
    he.event_type.should.equal("DecisionTaskStarted")
    he.event_timestamp.should.equal(1420110000.0)

@freeze_time("2015-01-01 12:00:00")
def test_history_event_to_dict_representation():
    he = HistoryEvent(123, "DecisionTaskStarted", scheduled_event_id=2)
    he.to_dict().should.equal({
        "eventId": 123,
        "eventType": "DecisionTaskStarted",
        "eventTimestamp": 1420110000.0,
        "decisionTaskStartedEventAttributes": {
            "scheduledEventId": 2
        }
    })

def test_history_event_breaks_on_initialization_if_not_implemented():
    HistoryEvent.when.called_with(
        123, "UnknownHistoryEvent"
    ).should.throw(NotImplementedError)


# DecisionTask
def test_decision_task_creation():
    wft = get_basic_workflow_type()
    wfe = WorkflowExecution(wft, "ab1234")
    dt = DecisionTask(wfe, 123)
    dt.workflow_execution.should.equal(wfe)
    dt.state.should.equal("SCHEDULED")
    dt.task_token.should_not.be.empty
    dt.started_event_id.should.be.none

def test_decision_task_full_dict_representation():
    wft = get_basic_workflow_type()
    wfe = WorkflowExecution(wft, "ab1234")
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
