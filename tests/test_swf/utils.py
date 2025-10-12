import boto3

from moto.core import DEFAULT_ACCOUNT_ID
from moto.swf.models import ActivityType, Domain, WorkflowExecution, WorkflowType

# Some useful constants
# Here are some activity timeouts we use in moto/swf tests ; they're extracted
# from semi-real world example, the goal is mostly to have predictable and
# intuitive behaviour in moto/swf own tests...
ACTIVITY_TASK_TIMEOUTS = {
    "heartbeatTimeout": "300",  # 5 mins
    "scheduleToStartTimeout": "1800",  # 30 mins
    "startToCloseTimeout": "1800",  # 30 mins
    "scheduleToCloseTimeout": "2700",  # 45 mins
}

# Some useful decisions
SCHEDULE_ACTIVITY_TASK_DECISION = {
    "decisionType": "ScheduleActivityTask",
    "scheduleActivityTaskDecisionAttributes": {
        "activityId": "my-activity-001",
        "activityType": {"name": "test-activity", "version": "v1.1"},
        "taskList": {"name": "activity-task-list"},
    },
}
for key, value in ACTIVITY_TASK_TIMEOUTS.items():
    SCHEDULE_ACTIVITY_TASK_DECISION["scheduleActivityTaskDecisionAttributes"][key] = (
        value
    )


# A test Domain
def get_basic_domain():
    return Domain("test-domain", "90", DEFAULT_ACCOUNT_ID, "us-east-1")


# A test WorkflowType
def _generic_workflow_type_attributes():
    return (
        ["test-workflow", "v1.0"],
        {
            "task_list": "queue",
            "default_child_policy": "ABANDON",
            "default_execution_start_to_close_timeout": "7200",
            "default_task_start_to_close_timeout": "300",
        },
    )


def _generic_workflow_type_attributes_boto3():
    return {
        "name": "test-workflow",
        "version": "v1.0",
        "defaultTaskList": {"name": "queue"},
        "defaultChildPolicy": "ABANDON",
        "defaultExecutionStartToCloseTimeout": "7200",
        "defaultTaskStartToCloseTimeout": "300",
    }


def get_basic_workflow_type():
    args, kwargs = _generic_workflow_type_attributes()
    return WorkflowType(*args, **kwargs)


def mock_basic_workflow_type(domain_name, conn):
    args, kwargs = _generic_workflow_type_attributes()
    conn.register_workflow_type(domain_name, *args, **kwargs)
    return conn


def mock_basic_workflow_type_boto3(domain_name, client):
    kwargs = _generic_workflow_type_attributes_boto3()
    client.register_workflow_type(domain=domain_name, **kwargs)
    return client


# A test WorkflowExecution
def make_workflow_execution(**kwargs):
    domain = get_basic_domain()
    domain.add_type(ActivityType("test-activity", "v1.1"))
    wft = get_basic_workflow_type()
    return WorkflowExecution(domain, wft, "ab1234", **kwargs)


# Makes decision tasks start automatically on a given workflow
def auto_start_decision_tasks(wfe):
    wfe.schedule_decision_task = wfe.schedule_and_start_decision_task
    return wfe


# Setup a complete example workflow and return the connection object
def setup_workflow_boto3():
    client = boto3.client("swf", region_name="us-west-1")
    client.register_domain(
        name="test-domain",
        workflowExecutionRetentionPeriodInDays="60",
        description="A test domain",
    )
    mock_basic_workflow_type_boto3("test-domain", client)
    client.register_activity_type(
        domain="test-domain",
        name="test-activity",
        version="v1.1",
        defaultTaskHeartbeatTimeout="600",
        defaultTaskScheduleToCloseTimeout="600",
        defaultTaskScheduleToStartTimeout="600",
        defaultTaskStartToCloseTimeout="600",
    )
    wfe = client.start_workflow_execution(
        domain="test-domain",
        workflowId="uid-abcd1234",
        workflowType={"name": "test-workflow", "version": "v1.0"},
    )
    client.run_id = wfe["runId"]
    return client


# A helper for processing the first timeout on a given object
def process_first_timeout(obj):
    _timeout = obj.first_timeout()
    if _timeout:
        obj.timeout(_timeout)
