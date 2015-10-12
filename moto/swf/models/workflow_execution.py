from __future__ import unicode_literals
import uuid

from moto.core.utils import camelcase_to_underscores

from ..exceptions import SWFDefaultUndefinedFault
from .decision_task import DecisionTask
from .history_event import HistoryEvent


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
        # events
        self._events = []
        # tasks
        self.decision_tasks = []
        self.activity_tasks = []
        self.child_workflow_executions = []

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
            "executionConfiguration": {
                "taskList": {"name": self.task_list}
            }
        }
        #configuration
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

    def events(self, reverse_order=False):
        if reverse_order:
            return reversed(self._events)
        else:
            return self._events

    def next_event_id(self):
        event_ids = [evt.event_id for evt in self._events]
        return max(event_ids or [0]) + 1

    def _add_event(self, *args, **kwargs):
        evt = HistoryEvent(self.next_event_id(), *args, **kwargs)
        self._events.append(evt)
        return evt

    def start(self):
        self._add_event(
            "WorkflowExecutionStarted",
            workflow_execution=self,
        )
        self.schedule_decision_task()

    def schedule_decision_task(self):
        self.open_counts["openDecisionTasks"] += 1
        evt = self._add_event(
            "DecisionTaskScheduled",
            workflow_execution=self,
        )
        self.decision_tasks.append(DecisionTask(self, evt.event_id))

    @property
    def scheduled_decision_tasks(self):
        return filter(
            lambda t: t.state == "SCHEDULED",
            self.decision_tasks
        )

    def _find_decision_task(self, task_token):
        for dt in self.decision_tasks:
            if dt.task_token == task_token:
                return dt
        raise ValueError(
            "No decision task with token: {}".format(task_token)
        )

    def start_decision_task(self, task_token, identity=None):
        dt = self._find_decision_task(task_token)
        evt = self._add_event(
            "DecisionTaskStarted",
            workflow_execution=self,
            scheduled_event_id=dt.scheduled_event_id,
            identity=identity
        )
        dt.start(evt.event_id)

    def complete_decision_task(self, task_token, decisions=None, execution_context=None):
        # TODO: check if decision can really complete in case of malformed "decisions"
        dt = self._find_decision_task(task_token)
        evt = self._add_event(
            "DecisionTaskCompleted",
            scheduled_event_id=dt.scheduled_event_id,
            started_event_id=dt.started_event_id,
            execution_context=execution_context,
        )
        dt.complete()
        self.handle_decisions(decisions)

    def handle_decisions(self, decisions):
        """
        Handles a Decision according to SWF docs.
        See: http://docs.aws.amazon.com/amazonswf/latest/apireference/API_Decision.html
        """
        # 'decisions' can be None per boto.swf defaults, so better exiting
        # directly for falsy values
        if not decisions:
            return
        # handle each decision separately, in order
        for decision in decisions:
            decision_type = decision["decisionType"]
            # TODO: implement Decision type: CancelTimer
            # TODO: implement Decision type: CancelWorkflowExecution
            # TODO: implement Decision type: CompleteWorkflowExecution
            # TODO: implement Decision type: ContinueAsNewWorkflowExecution
            # TODO: implement Decision type: FailWorkflowExecution
            # TODO: implement Decision type: RecordMarker
            # TODO: implement Decision type: RequestCancelActivityTask
            # TODO: implement Decision type: RequestCancelExternalWorkflowExecution
            # TODO: implement Decision type: ScheduleActivityTask
            # TODO: implement Decision type: ScheduleLambdaFunction
            # TODO: implement Decision type: SignalExternalWorkflowExecution
            # TODO: implement Decision type: StartChildWorkflowExecution
            # TODO: implement Decision type: StartTimer
            raise NotImplementedError("Cannot handle decision: {}".format(decision_type))
