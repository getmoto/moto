from __future__ import unicode_literals
import uuid

from moto.core.utils import camelcase_to_underscores


class WorkflowExecution(object):
    def __init__(self, workflow_type, workflow_id, **kwargs):
        self.workflow_type = workflow_type
        self.workflow_id = workflow_id
        self.run_id = uuid.uuid4().hex
        self.execution_status = "OPEN"
        self.cancel_requested = False
        #config
        for key, value in kwargs.iteritems():
            self.__setattr__(key, value)
        #counters
        self.open_counts = {
            "openTimers": 0,
            "openDecisionTasks": 0,
            "openActivityTasks": 0,
            "openChildWorkflowExecutions": 0,
        }

    def __repr__(self):
        return "WorkflowExecution(run_id: {})".format(self.run_id)

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
