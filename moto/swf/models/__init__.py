from __future__ import unicode_literals

from boto3 import Session

from moto.core import BaseBackend

from ..exceptions import (
    SWFUnknownResourceFault,
    SWFDomainAlreadyExistsFault,
    SWFDomainDeprecatedFault,
    SWFTypeAlreadyExistsFault,
    SWFTypeDeprecatedFault,
    SWFValidationException,
)
from .activity_task import ActivityTask  # noqa
from .activity_type import ActivityType  # noqa
from .decision_task import DecisionTask  # noqa
from .domain import Domain  # noqa
from .generic_type import GenericType  # noqa
from .history_event import HistoryEvent  # noqa
from .timeout import Timeout  # noqa
from .workflow_type import WorkflowType  # noqa
from .workflow_execution import WorkflowExecution  # noqa
from time import sleep

KNOWN_SWF_TYPES = {"activity": ActivityType, "workflow": WorkflowType}


class SWFBackend(BaseBackend):
    def __init__(self, region_name):
        self.region_name = region_name
        self.domains = []
        super(SWFBackend, self).__init__()

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    def _get_domain(self, name, ignore_empty=False):
        matching = [domain for domain in self.domains if domain.name == name]
        if not matching and not ignore_empty:
            raise SWFUnknownResourceFault("domain", name)
        if matching:
            return matching[0]
        return None

    def _process_timeouts(self):
        for domain in self.domains:
            for wfe in domain.workflow_executions:
                wfe._process_timeouts()

    def list_domains(self, status, reverse_order=None):
        domains = [domain for domain in self.domains if domain.status == status]
        domains = sorted(domains, key=lambda domain: domain.name)
        if reverse_order:
            domains = reversed(domains)
        return domains

    def list_open_workflow_executions(
        self, domain_name, maximum_page_size, tag_filter, reverse_order, **kwargs
    ):
        self._process_timeouts()
        domain = self._get_domain(domain_name)
        if domain.status == "DEPRECATED":
            raise SWFDomainDeprecatedFault(domain_name)
        open_wfes = [
            wfe for wfe in domain.workflow_executions if wfe.execution_status == "OPEN"
        ]

        if tag_filter:
            for open_wfe in open_wfes:
                if tag_filter["tag"] not in open_wfe.tag_list:
                    open_wfes.remove(open_wfe)
        if reverse_order:
            open_wfes = reversed(open_wfes)
        return open_wfes[0:maximum_page_size]

    def list_closed_workflow_executions(
        self,
        domain_name,
        close_time_filter,
        tag_filter,
        close_status_filter,
        maximum_page_size,
        reverse_order,
        **kwargs
    ):
        self._process_timeouts()
        domain = self._get_domain(domain_name)
        if domain.status == "DEPRECATED":
            raise SWFDomainDeprecatedFault(domain_name)
        closed_wfes = [
            wfe
            for wfe in domain.workflow_executions
            if wfe.execution_status == "CLOSED"
        ]
        if tag_filter:
            for closed_wfe in closed_wfes:
                if tag_filter["tag"] not in closed_wfe.tag_list:
                    closed_wfes.remove(closed_wfe)
        if close_status_filter:
            for closed_wfe in closed_wfes:
                if close_status_filter != closed_wfe.close_status:
                    closed_wfes.remove(closed_wfe)
        if reverse_order:
            closed_wfes = reversed(closed_wfes)
        return closed_wfes[0:maximum_page_size]

    def register_domain(
        self, name, workflow_execution_retention_period_in_days, description=None
    ):
        if self._get_domain(name, ignore_empty=True):
            raise SWFDomainAlreadyExistsFault(name)
        domain = Domain(
            name,
            workflow_execution_retention_period_in_days,
            self.region_name,
            description,
        )
        self.domains.append(domain)

    def deprecate_domain(self, name):
        domain = self._get_domain(name)
        if domain.status == "DEPRECATED":
            raise SWFDomainDeprecatedFault(name)
        domain.status = "DEPRECATED"

    def undeprecate_domain(self, name):
        domain = self._get_domain(name)
        if domain.status == "REGISTERED":
            raise SWFDomainAlreadyExistsFault(name)
        domain.status = "REGISTERED"

    def describe_domain(self, name):
        return self._get_domain(name)

    def list_types(self, kind, domain_name, status, reverse_order=None):
        domain = self._get_domain(domain_name)
        _types = domain.find_types(kind, status)
        _types = sorted(_types, key=lambda domain: domain.name)
        if reverse_order:
            _types = reversed(_types)
        return _types

    def register_type(self, kind, domain_name, name, version, **kwargs):
        domain = self._get_domain(domain_name)
        _type = domain.get_type(kind, name, version, ignore_empty=True)
        if _type:
            raise SWFTypeAlreadyExistsFault(_type)
        _class = KNOWN_SWF_TYPES[kind]
        _type = _class(name, version, **kwargs)
        domain.add_type(_type)

    def deprecate_type(self, kind, domain_name, name, version):
        domain = self._get_domain(domain_name)
        _type = domain.get_type(kind, name, version)
        if _type.status == "DEPRECATED":
            raise SWFTypeDeprecatedFault(_type)
        _type.status = "DEPRECATED"

    def undeprecate_type(self, kind, domain_name, name, version):
        domain = self._get_domain(domain_name)
        _type = domain.get_type(kind, name, version)
        if _type.status == "REGISTERED":
            raise SWFTypeAlreadyExistsFault(_type)
        _type.status = "REGISTERED"

    def describe_type(self, kind, domain_name, name, version):
        domain = self._get_domain(domain_name)
        return domain.get_type(kind, name, version)

    def start_workflow_execution(
        self,
        domain_name,
        workflow_id,
        workflow_name,
        workflow_version,
        tag_list=None,
        input=None,
        **kwargs
    ):
        domain = self._get_domain(domain_name)
        wf_type = domain.get_type("workflow", workflow_name, workflow_version)
        if wf_type.status == "DEPRECATED":
            raise SWFTypeDeprecatedFault(wf_type)
        wfe = WorkflowExecution(
            domain, wf_type, workflow_id, tag_list=tag_list, input=input, **kwargs
        )
        domain.add_workflow_execution(wfe)
        wfe.start()

        return wfe

    def describe_workflow_execution(self, domain_name, run_id, workflow_id):
        # process timeouts on all objects
        self._process_timeouts()
        domain = self._get_domain(domain_name)
        return domain.get_workflow_execution(workflow_id, run_id=run_id)

    def poll_for_decision_task(self, domain_name, task_list, identity=None):
        # process timeouts on all objects
        self._process_timeouts()
        domain = self._get_domain(domain_name)
        # Real SWF cases:
        # - case 1: there's a decision task to return, return it
        # - case 2: there's no decision task to return, so wait for timeout
        #           and if a new decision is schedule, start and return it
        # - case 3: timeout reached, no decision, return an empty decision
        #           (e.g. a decision with an empty "taskToken")
        #
        # For the sake of simplicity, we forget case 2 for now, so either
        # there's a DecisionTask to return, either we return a blank one.
        #
        # SWF client libraries should cope with that easily as long as tests
        # aren't distributed.
        #
        # TODO: handle long polling (case 2) for decision tasks
        candidates = []
        for _task_list, tasks in domain.decision_task_lists.items():
            if _task_list == task_list:
                candidates += [t for t in tasks if t.state == "SCHEDULED"]
        if any(candidates):
            # TODO: handle task priorities (but not supported by boto for now)
            task = min(candidates, key=lambda d: d.scheduled_at)
            wfe = task.workflow_execution
            wfe.start_decision_task(task.task_token, identity=identity)
            return task
        else:
            # Sleeping here will prevent clients that rely on the timeout from
            # entering in a busy waiting loop.
            sleep(1)
            return None

    def count_pending_decision_tasks(self, domain_name, task_list):
        # process timeouts on all objects
        self._process_timeouts()
        domain = self._get_domain(domain_name)
        count = 0
        for wfe in domain.workflow_executions:
            if wfe.task_list == task_list:
                count += wfe.open_counts["openDecisionTasks"]
        return count

    def respond_decision_task_completed(
        self, task_token, decisions=None, execution_context=None
    ):
        # process timeouts on all objects
        self._process_timeouts()
        # let's find decision task
        decision_task = None
        for domain in self.domains:
            for wfe in domain.workflow_executions:
                for dt in wfe.decision_tasks:
                    if dt.task_token == task_token:
                        decision_task = dt
        # no decision task found
        if not decision_task:
            # In the real world, SWF distinguishes an obviously invalid token and a
            # token that has no corresponding decision task. For the latter it seems
            # to wait until a task with that token comes up (which looks like a smart
            # choice in an eventually-consistent system). The call doesn't seem to
            # timeout shortly, it takes 3 or 4 minutes to result in:
            #    BotoServerError: 500 Internal Server Error
            #    {"__type":"com.amazon.coral.service#InternalFailure"}
            # This behavior is not documented clearly in SWF docs and we'll ignore it
            # in moto, as there is no obvious reason to rely on it in tests.
            raise SWFValidationException("Invalid token")
        # decision task found, but WorflowExecution is CLOSED
        wfe = decision_task.workflow_execution
        if not wfe.open:
            raise SWFUnknownResourceFault(
                "execution",
                "WorkflowExecution=[workflowId={0}, runId={1}]".format(
                    wfe.workflow_id, wfe.run_id
                ),
            )
        # decision task found, but already completed
        if decision_task.state != "STARTED":
            if decision_task.state == "COMPLETED":
                raise SWFUnknownResourceFault(
                    "decision task, scheduledEventId = {0}".format(
                        decision_task.scheduled_event_id
                    )
                )
            else:
                raise ValueError(
                    "This shouldn't happen: you have to PollForDecisionTask to get a token, "
                    "which changes DecisionTask status to 'STARTED' ; then it can only change "
                    "to 'COMPLETED'. If you didn't hack moto/swf internals, this is probably "
                    "a bug in moto, please report it, thanks!"
                )
        # everything's good
        if decision_task:
            wfe = decision_task.workflow_execution
            wfe.complete_decision_task(
                decision_task.task_token,
                decisions=decisions,
                execution_context=execution_context,
            )

    def poll_for_activity_task(self, domain_name, task_list, identity=None):
        # process timeouts on all objects
        self._process_timeouts()
        domain = self._get_domain(domain_name)
        # Real SWF cases:
        # - case 1: there's an activity task to return, return it
        # - case 2: there's no activity task to return, so wait for timeout
        #           and if a new activity is scheduled, return it
        # - case 3: timeout reached, no activity task, return an empty response
        #           (e.g. a response with an empty "taskToken")
        #
        # For the sake of simplicity, we forget case 2 for now, so either
        # there's an ActivityTask to return, either we return a blank one.
        #
        # SWF client libraries should cope with that easily as long as tests
        # aren't distributed.
        #
        # TODO: handle long polling (case 2) for activity tasks
        candidates = []
        for _task_list, tasks in domain.activity_task_lists.items():
            if _task_list == task_list:
                candidates += [t for t in tasks if t.state == "SCHEDULED"]
        if any(candidates):
            # TODO: handle task priorities (but not supported by boto for now)
            task = min(candidates, key=lambda d: d.scheduled_at)
            wfe = task.workflow_execution
            wfe.start_activity_task(task.task_token, identity=identity)
            return task
        else:
            # Sleeping here will prevent clients that rely on the timeout from
            # entering in a busy waiting loop.
            sleep(1)
            return None

    def count_pending_activity_tasks(self, domain_name, task_list):
        # process timeouts on all objects
        self._process_timeouts()
        domain = self._get_domain(domain_name)
        count = 0
        for _task_list, tasks in domain.activity_task_lists.items():
            if _task_list == task_list:
                pending = [t for t in tasks if t.state in ["SCHEDULED", "STARTED"]]
                count += len(pending)
        return count

    def _find_activity_task_from_token(self, task_token):
        activity_task = None
        for domain in self.domains:
            for wfe in domain.workflow_executions:
                for task in wfe.activity_tasks:
                    if task.task_token == task_token:
                        activity_task = task
        # no task found
        if not activity_task:
            # Same as for decision tasks, we raise an invalid token BOTH for clearly
            # wrong SWF tokens and OK tokens but not used correctly. This should not
            # be a problem in moto.
            raise SWFValidationException("Invalid token")
        # activity task found, but WorflowExecution is CLOSED
        wfe = activity_task.workflow_execution
        if not wfe.open:
            raise SWFUnknownResourceFault(
                "execution",
                "WorkflowExecution=[workflowId={0}, runId={1}]".format(
                    wfe.workflow_id, wfe.run_id
                ),
            )
        # activity task found, but already completed
        if activity_task.state != "STARTED":
            if activity_task.state == "COMPLETED":
                raise SWFUnknownResourceFault(
                    "activity, scheduledEventId = {0}".format(
                        activity_task.scheduled_event_id
                    )
                )
            else:
                raise ValueError(
                    "This shouldn't happen: you have to PollForActivityTask to get a token, "
                    "which changes ActivityTask status to 'STARTED' ; then it can only change "
                    "to 'COMPLETED'. If you didn't hack moto/swf internals, this is probably "
                    "a bug in moto, please report it, thanks!"
                )
        # everything's good
        return activity_task

    def respond_activity_task_completed(self, task_token, result=None):
        # process timeouts on all objects
        self._process_timeouts()
        activity_task = self._find_activity_task_from_token(task_token)
        wfe = activity_task.workflow_execution
        wfe.complete_activity_task(activity_task.task_token, result=result)

    def respond_activity_task_failed(self, task_token, reason=None, details=None):
        # process timeouts on all objects
        self._process_timeouts()
        activity_task = self._find_activity_task_from_token(task_token)
        wfe = activity_task.workflow_execution
        wfe.fail_activity_task(activity_task.task_token, reason=reason, details=details)

    def terminate_workflow_execution(
        self,
        domain_name,
        workflow_id,
        child_policy=None,
        details=None,
        reason=None,
        run_id=None,
    ):
        # process timeouts on all objects
        self._process_timeouts()
        domain = self._get_domain(domain_name)
        wfe = domain.get_workflow_execution(
            workflow_id, run_id=run_id, raise_if_closed=True
        )
        wfe.terminate(child_policy=child_policy, details=details, reason=reason)

    def record_activity_task_heartbeat(self, task_token, details=None):
        # process timeouts on all objects
        self._process_timeouts()
        activity_task = self._find_activity_task_from_token(task_token)
        activity_task.reset_heartbeat_clock()
        if details:
            activity_task.details = details

    def signal_workflow_execution(
        self, domain_name, signal_name, workflow_id, input=None, run_id=None
    ):
        # process timeouts on all objects
        self._process_timeouts()
        domain = self._get_domain(domain_name)
        wfe = domain.get_workflow_execution(
            workflow_id, run_id=run_id, raise_if_closed=True
        )
        wfe.signal(signal_name, input)


swf_backends = {}
for region in Session().get_available_regions("swf"):
    swf_backends[region] = SWFBackend(region)
for region in Session().get_available_regions("swf", partition_name="aws-us-gov"):
    swf_backends[region] = SWFBackend(region)
for region in Session().get_available_regions("swf", partition_name="aws-cn"):
    swf_backends[region] = SWFBackend(region)
