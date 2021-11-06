from datetime import datetime
import uuid

from moto.core import BaseModel
from moto.core.utils import unix_time
from ..exceptions import SWFWorkflowExecutionClosedError

from .timeout import Timeout


class ActivityTask(BaseModel):
    def __init__(
        self,
        activity_id,
        activity_type,
        scheduled_event_id,
        workflow_execution,
        timeouts,
        input=None,
    ):
        self.activity_id = activity_id
        self.activity_type = activity_type
        self.details = None
        self.input = input
        self.last_heartbeat_timestamp = unix_time()
        self.scheduled_event_id = scheduled_event_id
        self.started_event_id = None
        self.state = "SCHEDULED"
        self.task_token = str(uuid.uuid4())
        self.timeouts = timeouts
        self.timeout_type = None
        self.workflow_execution = workflow_execution
        # this is *not* necessarily coherent with workflow execution history,
        # but that shouldn't be a problem for tests
        self.scheduled_at = datetime.utcnow()

    def _check_workflow_execution_open(self):
        if not self.workflow_execution.open:
            raise SWFWorkflowExecutionClosedError()

    @property
    def open(self):
        return self.state in ["SCHEDULED", "STARTED"]

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
        self._check_workflow_execution_open()
        self.state = "COMPLETED"

    def fail(self):
        self._check_workflow_execution_open()
        self.state = "FAILED"

    def reset_heartbeat_clock(self):
        self.last_heartbeat_timestamp = unix_time()

    def first_timeout(self):
        if not self.open or not self.workflow_execution.open:
            return None

        if self.timeouts["heartbeatTimeout"] == "NONE":
            return None

        heartbeat_timeout_at = self.last_heartbeat_timestamp + int(
            self.timeouts["heartbeatTimeout"]
        )
        _timeout = Timeout(self, heartbeat_timeout_at, "HEARTBEAT")
        if _timeout.reached:
            return _timeout

    def process_timeouts(self):
        _timeout = self.first_timeout()
        if _timeout:
            self.timeout(_timeout)

    def timeout(self, _timeout):
        self._check_workflow_execution_open()
        self.state = "TIMED_OUT"
        self.timeout_type = _timeout.kind
