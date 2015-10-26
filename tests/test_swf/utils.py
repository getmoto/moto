import boto

from moto import mock_swf
from moto.swf.models import (
    ActivityType,
    Domain,
    WorkflowType,
    WorkflowExecution,
)


# A test Domain
def get_basic_domain():
    return Domain("test-domain", "90")


# A test WorkflowType
def _generic_workflow_type_attributes():
    return [
        "test-workflow", "v1.0"
    ], {
        "task_list": "queue",
        "default_child_policy": "ABANDON",
        "default_execution_start_to_close_timeout": "300",
        "default_task_start_to_close_timeout": "300",
    }

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


# Setup a complete example workflow and return the connection object
@mock_swf
def setup_workflow():
    conn = boto.connect_swf("the_key", "the_secret")
    conn.register_domain("test-domain", "60", description="A test domain")
    conn = mock_basic_workflow_type("test-domain", conn)
    conn.register_activity_type(
        "test-domain", "test-activity", "v1.1",
        default_task_heartbeat_timeout="600",
        default_task_schedule_to_close_timeout="600",
        default_task_schedule_to_start_timeout="600",
        default_task_start_to_close_timeout="600",
    )
    wfe = conn.start_workflow_execution("test-domain", "uid-abcd1234", "test-workflow", "v1.0")
    conn.run_id = wfe["runId"]
    return conn
