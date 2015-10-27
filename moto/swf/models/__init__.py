from __future__ import unicode_literals

import boto.swf

from moto.core import BaseBackend

from ..exceptions import (
    SWFUnknownResourceFault,
    SWFDomainAlreadyExistsFault,
    SWFDomainDeprecatedFault,
    SWFSerializationException,
    SWFTypeAlreadyExistsFault,
    SWFTypeDeprecatedFault,
    SWFValidationException,
)
from .activity_task import ActivityTask
from .activity_type import ActivityType
from .decision_task import DecisionTask
from .domain import Domain
from .generic_type import GenericType
from .history_event import HistoryEvent
from .workflow_type import WorkflowType
from .workflow_execution import WorkflowExecution


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

    def _check_none_or_string(self, parameter):
        if parameter is not None:
            self._check_string(parameter)

    def _check_string(self, parameter):
        if not isinstance(parameter, basestring):
            raise SWFSerializationException(parameter)

    def _check_none_or_list_of_strings(self, parameter):
        if parameter is not None:
            self._check_list_of_strings(parameter)

    def _check_list_of_strings(self, parameter):
        if not isinstance(parameter, list):
            raise SWFSerializationException(parameter)
        for i in parameter:
            if not isinstance(i, basestring):
                raise SWFSerializationException(parameter)

    def list_domains(self, status, reverse_order=None):
        self._check_string(status)
        domains = [domain for domain in self.domains
                   if domain.status == status]
        domains = sorted(domains, key=lambda domain: domain.name)
        if reverse_order:
            domains = reversed(domains)
        return domains

    def register_domain(self, name, workflow_execution_retention_period_in_days,
                        description=None):
        self._check_string(name)
        self._check_string(workflow_execution_retention_period_in_days)
        self._check_none_or_string(description)
        if self._get_domain(name, ignore_empty=True):
            raise SWFDomainAlreadyExistsFault(name)
        domain = Domain(name, workflow_execution_retention_period_in_days,
                        description)
        self.domains.append(domain)

    def deprecate_domain(self, name):
        self._check_string(name)
        domain = self._get_domain(name)
        if domain.status == "DEPRECATED":
            raise SWFDomainDeprecatedFault(name)
        domain.status = "DEPRECATED"

    def describe_domain(self, name):
        self._check_string(name)
        return self._get_domain(name)

    def list_types(self, kind, domain_name, status, reverse_order=None):
        self._check_string(domain_name)
        self._check_string(status)
        domain = self._get_domain(domain_name)
        _types = domain.find_types(kind, status)
        _types = sorted(_types, key=lambda domain: domain.name)
        if reverse_order:
            _types = reversed(_types)
        return _types

    def register_type(self, kind, domain_name, name, version, **kwargs):
        self._check_string(domain_name)
        self._check_string(name)
        self._check_string(version)
        for _, value in kwargs.iteritems():
            self._check_none_or_string(value)
        domain = self._get_domain(domain_name)
        _type = domain.get_type(kind, name, version, ignore_empty=True)
        if _type:
            raise SWFTypeAlreadyExistsFault(_type)
        _class = globals()["{}Type".format(kind.capitalize())]
        _type = _class(name, version, **kwargs)
        domain.add_type(_type)

    def deprecate_type(self, kind, domain_name, name, version):
        self._check_string(domain_name)
        self._check_string(name)
        self._check_string(version)
        domain = self._get_domain(domain_name)
        _type = domain.get_type(kind, name, version)
        if _type.status == "DEPRECATED":
            raise SWFTypeDeprecatedFault(_type)
        _type.status = "DEPRECATED"

    def describe_type(self, kind, domain_name, name, version):
        self._check_string(domain_name)
        self._check_string(name)
        self._check_string(version)
        domain = self._get_domain(domain_name)
        return domain.get_type(kind, name, version)

    def start_workflow_execution(self, domain_name, workflow_id,
                                 workflow_name, workflow_version,
                                 tag_list=None, **kwargs):
        self._check_string(domain_name)
        self._check_string(workflow_id)
        self._check_string(workflow_name)
        self._check_string(workflow_version)
        self._check_none_or_list_of_strings(tag_list)
        for _, value in kwargs.iteritems():
            self._check_none_or_string(value)

        domain = self._get_domain(domain_name)
        wf_type = domain.get_type("workflow", workflow_name, workflow_version)
        if wf_type.status == "DEPRECATED":
            raise SWFTypeDeprecatedFault(wf_type)
        wfe = WorkflowExecution(domain, wf_type, workflow_id,
                                tag_list=tag_list, **kwargs)
        domain.add_workflow_execution(wfe)
        wfe.start()

        return wfe

    def describe_workflow_execution(self, domain_name, run_id, workflow_id):
        self._check_string(domain_name)
        self._check_string(run_id)
        self._check_string(workflow_id)
        domain = self._get_domain(domain_name)
        return domain.get_workflow_execution(run_id, workflow_id)

    def poll_for_decision_task(self, domain_name, task_list, identity=None):
        self._check_string(domain_name)
        self._check_string(task_list)
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
        for _task_list, tasks in domain.decision_task_lists.iteritems():
            if _task_list == task_list:
                candidates += filter(lambda t: t.state == "SCHEDULED", tasks)
        if any(candidates):
            # TODO: handle task priorities (but not supported by boto for now)
            task = min(candidates, key=lambda d: d.scheduled_at)
            wfe = task.workflow_execution
            wfe.start_decision_task(task.task_token, identity=identity)
            return task
        else:
            return None

    def count_pending_decision_tasks(self, domain_name, task_list):
        self._check_string(domain_name)
        self._check_string(task_list)
        domain = self._get_domain(domain_name)
        count = 0
        for _, wfe in domain.workflow_executions.iteritems():
            if wfe.task_list == task_list:
                count += wfe.open_counts["openDecisionTasks"]
        return count

    def respond_decision_task_completed(self, task_token,
                                        decisions=None,
                                        execution_context=None):
        self._check_string(task_token)
        self._check_none_or_string(execution_context)
        # let's find decision task
        decision_task = None
        for domain in self.domains:
            for _, wfe in domain.workflow_executions.iteritems():
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
        if wfe.execution_status != "OPEN":
            raise SWFUnknownResourceFault(
                "execution",
                "WorkflowExecution=[workflowId={}, runId={}]".format(
                    wfe.workflow_id, wfe.run_id
                )
            )
        # decision task found, but already completed
        if decision_task.state != "STARTED":
            if decision_task.state == "COMPLETED":
                raise SWFUnknownResourceFault(
                    "decision task, scheduledEventId = {}".format(decision_task.scheduled_event_id)
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
            wfe.complete_decision_task(decision_task.task_token,
                                       decisions=decisions,
                                       execution_context=execution_context)

    def poll_for_activity_task(self, domain_name, task_list, identity=None):
        self._check_string(domain_name)
        self._check_string(task_list)
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
        for _task_list, tasks in domain.activity_task_lists.iteritems():
            if _task_list == task_list:
                candidates += filter(lambda t: t.state == "SCHEDULED", tasks)
        if any(candidates):
            # TODO: handle task priorities (but not supported by boto for now)
            task = min(candidates, key=lambda d: d.scheduled_at)
            wfe = task.workflow_execution
            wfe.start_activity_task(task.task_token, identity=identity)
            return task
        else:
            return None

    def count_pending_activity_tasks(self, domain_name, task_list):
        self._check_string(domain_name)
        self._check_string(task_list)
        domain = self._get_domain(domain_name)
        count = 0
        for _task_list, tasks in domain.activity_task_lists.iteritems():
            if _task_list == task_list:
                pending = [t for t in tasks if t.state in ["SCHEDULED", "STARTED"]]
                count += len(pending)
        return count

    def respond_activity_task_completed(self, task_token, result=None):
        self._check_string(task_token)
        self._check_none_or_string(result)
        # let's find the activity task
        activity_task = None
        for domain in self.domains:
            for _, wfe in domain.workflow_executions.iteritems():
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
        if wfe.execution_status != "OPEN":
            raise SWFUnknownResourceFault(
                "execution",
                "WorkflowExecution=[workflowId={}, runId={}]".format(
                    wfe.workflow_id, wfe.run_id
                )
            )
        # activity task found, but already completed
        if activity_task.state != "STARTED":
            if activity_task.state == "COMPLETED":
                raise SWFUnknownResourceFault(
                    "activity, scheduledEventId = {}".format(activity_task.scheduled_event_id)
                )
            else:
                raise ValueError(
                    "This shouldn't happen: you have to PollForActivityTask to get a token, "
                    "which changes ActivityTask status to 'STARTED' ; then it can only change "
                    "to 'COMPLETED'. If you didn't hack moto/swf internals, this is probably "
                    "a bug in moto, please report it, thanks!"
                )
        # everything's good
        if activity_task:
            wfe = activity_task.workflow_execution
            wfe.complete_activity_task(activity_task.task_token, result=result)


swf_backends = {}
for region in boto.swf.regions():
    swf_backends[region.name] = SWFBackend(region.name)
