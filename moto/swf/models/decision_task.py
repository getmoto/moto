from datetime import datetime

from moto.core import BaseModel
from moto.core.utils import unix_time
from moto.moto_api._internal import mock_random
from ..exceptions import SWFWorkflowExecutionClosedError

from .timeout import Timeout


class DecisionTask(BaseModel):
    def __init__(self, workflow_execution, scheduled_event_id):
        self.workflow_execution = workflow_execution
        self.workflow_type = workflow_execution.workflow_type
        self.task_token = str(mock_random.uuid4())
        self.scheduled_event_id = scheduled_event_id
        self.previous_started_event_id = None
        self.started_event_id = None
        self.started_timestamp = None
        self.start_to_close_timeout = (
            self.workflow_execution.task_start_to_close_timeout
        )
        self.state = "SCHEDULED"
        # this is *not* necessarily coherent with workflow execution history,
        # but that shouldn't be a problem for tests
        self.scheduled_at = datetime.utcnow()
        self.timeout_type = None

    @property
    def started(self):
        return self.state == "STARTED"

    def _check_workflow_execution_open(self):
        if not self.workflow_execution.open:
            raise SWFWorkflowExecutionClosedError()

    def to_full_dict(self, reverse_order=False):
        events = self.workflow_execution.events(reverse_order=reverse_order)
        hsh = {
            "events": [evt.to_dict() for evt in events],
            "taskToken": self.task_token,
            "workflowExecution": self.workflow_execution.to_short_dict(),
            "workflowType": self.workflow_type.to_short_dict(),
        }
        if self.previous_started_event_id is not None:
            hsh["previousStartedEventId"] = self.previous_started_event_id
        if self.started_event_id:
            hsh["startedEventId"] = self.started_event_id
        return hsh

    def start(self, started_event_id, previous_started_event_id=None):
        self.state = "STARTED"
        self.started_timestamp = unix_time()
        self.started_event_id = started_event_id
        self.previous_started_event_id = previous_started_event_id

    def complete(self):
        self._check_workflow_execution_open()
        self.state = "COMPLETED"

    def first_timeout(self):
        if not self.started or not self.workflow_execution.open:
            return None
        # TODO: handle the "NONE" case
        start_to_close_at = self.started_timestamp + int(self.start_to_close_timeout)
        _timeout = Timeout(self, start_to_close_at, "START_TO_CLOSE")
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
