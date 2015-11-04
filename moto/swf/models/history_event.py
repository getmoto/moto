from __future__ import unicode_literals
from datetime import datetime
from time import mktime

from ..utils import decapitalize, now_timestamp


class HistoryEvent(object):
    def __init__(self, event_id, event_type, **kwargs):
        self.event_id = event_id
        self.event_type = event_type
        self.event_timestamp = now_timestamp()
        for key, value in kwargs.items():
            self.__setattr__(key, value)
        # break soon if attributes are not valid
        self.event_attributes()

    def to_dict(self):
        return {
            "eventId": self.event_id,
            "eventType": self.event_type,
            "eventTimestamp": self.event_timestamp,
            self._attributes_key(): self.event_attributes()
        }

    def _attributes_key(self):
        key = "{0}EventAttributes".format(self.event_type)
        return decapitalize(key)

    def event_attributes(self):
        if self.event_type == "WorkflowExecutionStarted":
            wfe = self.workflow_execution
            hsh = {
                "childPolicy": wfe.child_policy,
                "executionStartToCloseTimeout": wfe.execution_start_to_close_timeout,
                "parentInitiatedEventId": 0,
                "taskList": {
                    "name": wfe.task_list
                },
                "taskStartToCloseTimeout": wfe.task_start_to_close_timeout,
                "workflowType": {
                    "name": wfe.workflow_type.name,
                    "version": wfe.workflow_type.version
                }
            }
            return hsh
        elif self.event_type == "DecisionTaskScheduled":
            wfe = self.workflow_execution
            return {
                "startToCloseTimeout": wfe.task_start_to_close_timeout,
                "taskList": {"name": wfe.task_list}
            }
        elif self.event_type == "DecisionTaskStarted":
            hsh = {
                "scheduledEventId": self.scheduled_event_id
            }
            if hasattr(self, "identity") and self.identity:
                hsh["identity"] = self.identity
            return hsh
        elif self.event_type == "DecisionTaskCompleted":
            hsh = {
                "scheduledEventId": self.scheduled_event_id,
                "startedEventId": self.started_event_id,
            }
            if hasattr(self, "execution_context") and self.execution_context:
                hsh["executionContext"] = self.execution_context
            return hsh
        elif self.event_type == "WorkflowExecutionCompleted":
            hsh = {
                "decisionTaskCompletedEventId": self.decision_task_completed_event_id,
            }
            if hasattr(self, "result") and self.result:
                hsh["result"] = self.result
            return hsh
        elif self.event_type == "WorkflowExecutionFailed":
            hsh = {
                "decisionTaskCompletedEventId": self.decision_task_completed_event_id,
            }
            if hasattr(self, "details") and self.details:
                hsh["details"] = self.details
            if hasattr(self, "reason") and self.reason:
                hsh["reason"] = self.reason
            return hsh
        elif self.event_type == "ActivityTaskScheduled":
            hsh = {
                "activityId": self.attributes["activityId"],
                "activityType": self.activity_type.to_short_dict(),
                "decisionTaskCompletedEventId": self.decision_task_completed_event_id,
                "taskList": {
                    "name": self.task_list,
                },
            }
            for attr in ["control", "heartbeatTimeout", "input", "scheduleToCloseTimeout",
                         "scheduleToStartTimeout", "startToCloseTimeout", "taskPriority"]:
                if self.attributes.get(attr):
                    hsh[attr] = self.attributes[attr]
            return hsh
        elif self.event_type == "ScheduleActivityTaskFailed":
            # TODO: implement other possible failure mode: OPEN_ACTIVITIES_LIMIT_EXCEEDED
            # NB: some failure modes are not implemented and probably won't be implemented in the
            # future, such as ACTIVITY_CREATION_RATE_EXCEEDED or OPERATION_NOT_PERMITTED
            return {
                "activityId": self.activity_id,
                "activityType": self.activity_type.to_short_dict(),
                "cause": self.cause,
                "decisionTaskCompletedEventId": self.decision_task_completed_event_id,
            }
        elif self.event_type == "ActivityTaskStarted":
            # TODO: merge it with DecisionTaskStarted
            hsh = {
                "scheduledEventId": self.scheduled_event_id
            }
            if hasattr(self, "identity") and self.identity:
                hsh["identity"] = self.identity
            return hsh
        elif self.event_type == "ActivityTaskCompleted":
            hsh = {
                "scheduledEventId": self.scheduled_event_id,
                "startedEventId": self.started_event_id,
            }
            if hasattr(self, "result") and self.result is not None:
                hsh["result"] = self.result
            return hsh
        elif self.event_type == "ActivityTaskFailed":
            # TODO: maybe merge it with ActivityTaskCompleted (different optional params tho)
            hsh = {
                "scheduledEventId": self.scheduled_event_id,
                "startedEventId": self.started_event_id,
            }
            if hasattr(self, "reason") and self.reason is not None:
                hsh["reason"] = self.reason
            if hasattr(self, "details") and self.details is not None:
                hsh["details"] = self.details
            return hsh
        elif self.event_type == "WorkflowExecutionTerminated":
            hsh = {
                "childPolicy": self.child_policy,
            }
            if self.cause:
                hsh["cause"] = self.cause
            if self.details:
                hsh["details"] = self.details
            if self.reason:
                hsh["reason"] = self.reason
            return hsh
        elif self.event_type == "ActivityTaskTimedOut":
            hsh = {
                "scheduledEventId": self.scheduled_event_id,
                "startedEventId": self.started_event_id,
                "timeoutType": self.timeout_type,
            }
            if self.details:
                hsh["details"] = self.details
            return hsh
        elif self.event_type == "DecisionTaskTimedOut":
            return {
                "scheduledEventId": self.scheduled_event_id,
                "startedEventId": self.started_event_id,
                "timeoutType": self.timeout_type,
            }
        elif self.event_type == "WorkflowExecutionTimedOut":
            return {
                "childPolicy": self.child_policy,
                "timeoutType": self.timeout_type,
            }
        else:
            raise NotImplementedError(
                "HistoryEvent does not implement attributes for type '{0}'".format(self.event_type)
            )
