import boto

from moto.swf.models import ActivityType, Domain, WorkflowType, WorkflowExecution


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
    SCHEDULE_ACTIVITY_TASK_DECISION["scheduleActivityTaskDecisionAttributes"][
        key
    ] = value


# A test Domain
def get_basic_domain():
    return Domain("test-domain", "90", "us-east-1")


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


def get_basic_workflow_type():
    args, kwargs = _generic_workflow_type_attributes()
    return WorkflowType(*args, **kwargs)


def mock_basic_workflow_type(domain_name, conn):
    args, kwargs = _generic_workflow_type_attributes()
    conn.register_workflow_type(domain_name, *args, **kwargs)
    return conn


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
def setup_workflow():
    conn = boto.connect_swf("the_key", "the_secret")
    conn.register_domain("test-domain", "60", description="A test domain")
    conn = mock_basic_workflow_type("test-domain", conn)
    conn.register_activity_type(
        "test-domain",
        "test-activity",
        "v1.1",
        default_task_heartbeat_timeout="600",
        default_task_schedule_to_close_timeout="600",
        default_task_schedule_to_start_timeout="600",
        default_task_start_to_close_timeout="600",
    )
    wfe = conn.start_workflow_execution(
        "test-domain", "uid-abcd1234", "test-workflow", "v1.0"
    )
    conn.run_id = wfe["runId"]
    return conn


# A helper for processing the first timeout on a given object
def process_first_timeout(obj):
    _timeout = obj.first_timeout()
    if _timeout:
        obj.timeout(_timeout)
