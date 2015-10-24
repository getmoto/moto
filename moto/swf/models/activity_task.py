from __future__ import unicode_literals
import uuid


class ActivityTask(object):
    def __init__(self, activity_id, activity_type, workflow_execution, input=None):
        self.activity_id = activity_id
        self.activity_type = activity_type
        self.input = input
        self.started_event_id = None
        self.state = "SCHEDULED"
        self.task_token = str(uuid.uuid4())
        self.workflow_execution = workflow_execution

    def start(self, started_event_id):
        self.state = "STARTED"
        self.started_event_id = started_event_id

    def complete(self):
        self.state = "COMPLETED"
