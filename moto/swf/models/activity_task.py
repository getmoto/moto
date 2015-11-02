from __future__ import unicode_literals
from datetime import datetime
import uuid

from ..utils import now_timestamp


class ActivityTask(object):
    def __init__(self, activity_id, activity_type, scheduled_event_id,
                 workflow_execution, input=None):
        self.activity_id = activity_id
        self.activity_type = activity_type
        self.input = input
        self.last_heartbeat_timestamp = now_timestamp()
        self.scheduled_event_id = scheduled_event_id
        self.started_event_id = None
        self.state = "SCHEDULED"
        self.task_token = str(uuid.uuid4())
        self.workflow_execution = workflow_execution
        # this is *not* necessarily coherent with workflow execution history,
        # but that shouldn't be a problem for tests
        self.scheduled_at = datetime.now()

    def to_full_dict(self):
        hsh = {
            "activityId": self.activity_id,
            "activityType": self.activity_type.to_short_dict(),
            "taskToken": self.task_token,
            "startedEventId": self.started_event_id,
            "workflowExecution": self.workflow_execution.to_short_dict(),
        }
        if self.input:
            hsh["input"] = self.input
        return hsh

    def start(self, started_event_id):
        self.state = "STARTED"
        self.started_event_id = started_event_id

    def complete(self):
        self.state = "COMPLETED"

    def fail(self):
        self.state = "FAILED"

    def reset_heartbeat_clock(self):
        self.last_heartbeat_timestamp = now_timestamp()
