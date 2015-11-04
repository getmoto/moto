from __future__ import unicode_literals
from datetime import datetime
import uuid

from ..utils import now_timestamp


class DecisionTask(object):
    def __init__(self, workflow_execution, scheduled_event_id):
        self.workflow_execution = workflow_execution
        self.workflow_type = workflow_execution.workflow_type
        self.task_token = str(uuid.uuid4())
        self.scheduled_event_id = scheduled_event_id
        self.previous_started_event_id = 0
        self.started_event_id = None
        self.started_timestamp = None
        self.start_to_close_timeout = self.workflow_execution.task_start_to_close_timeout
        self.state = "SCHEDULED"
        # this is *not* necessarily coherent with workflow execution history,
        # but that shouldn't be a problem for tests
        self.scheduled_at = datetime.now()
        self.timeout_type = None

    def to_full_dict(self, reverse_order=False):
        events = self.workflow_execution.events(reverse_order=reverse_order)
        hsh = {
            "events": [
                evt.to_dict() for evt in events
            ],
            "taskToken": self.task_token,
            "previousStartedEventId": self.previous_started_event_id,
            "workflowExecution": self.workflow_execution.to_short_dict(),
            "workflowType": self.workflow_type.to_short_dict(),
        }
        if self.started_event_id:
            hsh["startedEventId"] = self.started_event_id
        return hsh

    def start(self, started_event_id):
        self.state = "STARTED"
        self.started_timestamp = now_timestamp()
        self.started_event_id = started_event_id

    def complete(self):
        self.state = "COMPLETED"

    def has_timedout(self):
        if self.state != "STARTED" or not self.workflow_execution.open:
            return False
        # TODO: handle the "NONE" case
        start_to_close_timeout = self.started_timestamp + \
                                    int(self.start_to_close_timeout)
        return start_to_close_timeout < now_timestamp()

    def process_timeouts(self):
        if self.has_timedout():
            self.state = "TIMED_OUT"
            self.timeout_type = "START_TO_CLOSE"
