from moto.core import BaseModel
from moto.core.utils import underscores_to_camelcase, unix_time

from ..utils import decapitalize


# We keep track of which history event types we support
# so that we'll be able to catch specific formatting
# for new events if needed.
SUPPORTED_HISTORY_EVENT_TYPES = (
    "WorkflowExecutionStarted",
    "DecisionTaskScheduled",
    "DecisionTaskStarted",
    "DecisionTaskCompleted",
    "WorkflowExecutionCompleted",
    "WorkflowExecutionFailed",
    "ActivityTaskScheduled",
    "ScheduleActivityTaskFailed",
    "ActivityTaskStarted",
    "ActivityTaskCompleted",
    "ActivityTaskFailed",
    "WorkflowExecutionTerminated",
    "ActivityTaskTimedOut",
    "DecisionTaskTimedOut",
    "WorkflowExecutionTimedOut",
    "WorkflowExecutionSignaled",
    "MarkerRecorded",
    "TimerStarted",
    "TimerCancelled",
    "TimerFired",
    "CancelTimerFailed",
    "StartTimerFailed",
    "WorkflowExecutionCanceled",
    "CancelWorkflowExecutionFailed",
)


class HistoryEvent(BaseModel):
    def __init__(self, event_id, event_type, event_timestamp=None, **kwargs):
        if event_type not in SUPPORTED_HISTORY_EVENT_TYPES:
            raise NotImplementedError(
                "HistoryEvent does not implement attributes for type '{0}'".format(
                    event_type
                )
            )
        self.event_id = event_id
        self.event_type = event_type
        if event_timestamp:
            self.event_timestamp = event_timestamp
        else:
            self.event_timestamp = unix_time()
        # pre-populate a dict: {"camelCaseKey": value}
        self.event_attributes = {}
        for key, value in kwargs.items():
            if value:
                camel_key = underscores_to_camelcase(key)
                if key == "task_list":
                    value = {"name": value}
                elif key == "workflow_type":
                    value = {"name": value.name, "version": value.version}
                elif key == "activity_type":
                    value = value.to_short_dict()
                self.event_attributes[camel_key] = value

    def to_dict(self):
        return {
            "eventId": self.event_id,
            "eventType": self.event_type,
            "eventTimestamp": self.event_timestamp,
            self._attributes_key(): self.event_attributes,
        }

    def _attributes_key(self):
        key = "{0}EventAttributes".format(self.event_type)
        return decapitalize(key)
