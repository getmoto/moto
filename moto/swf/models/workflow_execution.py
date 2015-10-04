from __future__ import unicode_literals
import uuid

from moto.core.utils import camelcase_to_underscores

from ..exceptions import SWFDefaultUndefinedFault


class WorkflowExecution(object):
    def __init__(self, workflow_type, workflow_id, **kwargs):
        self.workflow_type = workflow_type
        self.workflow_id = workflow_id
        self.run_id = uuid.uuid4().hex
        self.execution_status = "OPEN"
        self.cancel_requested = False
        # args processing
        # NB: the order follows boto/SWF order of exceptions appearance (if no
        # param is set, # SWF will raise DefaultUndefinedFault errors in the
        # same order as the few lines that follow)
        self._set_from_kwargs_or_workflow_type(kwargs, "execution_start_to_close_timeout")
        self._set_from_kwargs_or_workflow_type(kwargs, "task_list", "task_list")
        self._set_from_kwargs_or_workflow_type(kwargs, "task_start_to_close_timeout")
        self._set_from_kwargs_or_workflow_type(kwargs, "child_policy")
        self.input = kwargs.get("input")
        # counters
        self.open_counts = {
            "openTimers": 0,
            "openDecisionTasks": 0,
            "openActivityTasks": 0,
            "openChildWorkflowExecutions": 0,
        }

    def __repr__(self):
        return "WorkflowExecution(run_id: {})".format(self.run_id)

    def _set_from_kwargs_or_workflow_type(self, kwargs, local_key, workflow_type_key=None):
        if workflow_type_key is None:
            workflow_type_key = "default_"+local_key
        value = kwargs.get(local_key)
        if not value and hasattr(self.workflow_type, workflow_type_key):
            value = getattr(self.workflow_type, workflow_type_key)
        if not value:
            raise SWFDefaultUndefinedFault(local_key)
        setattr(self, local_key, value)

    @property
    def _configuration_keys(self):
        return [
            "executionStartToCloseTimeout",
            "childPolicy",
            "taskPriority",
            "taskStartToCloseTimeout",
        ]

    def to_short_dict(self):
        return {
            "workflowId": self.workflow_id,
            "runId": self.run_id
        }

    def to_medium_dict(self):
        hsh = {
            "execution": self.to_short_dict(),
            "workflowType": self.workflow_type.to_short_dict(),
            "startTimestamp": 1420066800.123,
            "executionStatus": self.execution_status,
            "cancelRequested": self.cancel_requested,
        }
        if hasattr(self, "tag_list"):
            hsh["tagList"] = self.tag_list
        return hsh

    def to_full_dict(self):
        hsh = {
            "executionInfo": self.to_medium_dict(),
            "executionConfiguration": {}
        }
        #configuration
        if hasattr(self, "task_list"):
            hsh["executionConfiguration"]["taskList"] = {"name": self.task_list}
        for key in self._configuration_keys:
            attr = camelcase_to_underscores(key)
            if not hasattr(self, attr):
                continue
            if not getattr(self, attr):
                continue
            hsh["executionConfiguration"][key] = getattr(self, attr)
        #counters
        hsh["openCounts"] = self.open_counts
        return hsh
