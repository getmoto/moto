from __future__ import unicode_literals
from datetime import datetime
from time import mktime


class HistoryEvent(object):
    def __init__(self, event_id, event_type, **kwargs):
        self.event_id = event_id
        self.event_type = event_type
        self.event_timestamp = float(mktime(datetime.now().timetuple()))
        for key, value in kwargs.iteritems():
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
        key = "{}EventAttributes".format(self.event_type)
        key = key[0].lower() + key[1:]
        return key

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
            return {
                "scheduledEventId": self.scheduled_event_id
            }
        else:
            raise NotImplementedError(
                "HistoryEvent does not implement attributes for type '{}'".format(self.event_type)
            )
