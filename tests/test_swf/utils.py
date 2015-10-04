from moto.swf.models import (
    WorkflowType,
)


# A generic test WorkflowType
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
