from __future__ import unicode_literals
from collections import defaultdict

from ..exceptions import (
    SWFUnknownResourceFault,
    SWFWorkflowExecutionAlreadyStartedFault,
)


class Domain(object):
    def __init__(self, name, retention, description=None):
        self.name = name
        self.retention = retention
        self.description = description
        self.status = "REGISTERED"
        self.types = {
            "activity": defaultdict(dict),
            "workflow": defaultdict(dict),
        }
        # Workflow executions have an id, which unicity is guaranteed
        # at domain level (not super clear in the docs, but I checked
        # that against SWF API) ; hence the storage method as a dict
        # of "workflow_id (client determined)" => WorkflowExecution()
        # here.
        self.workflow_executions = {}
        self.task_lists = defaultdict(list)

    def __repr__(self):
        return "Domain(name: %(name)s, status: %(status)s)" % self.__dict__

    def to_short_dict(self):
        hsh = {
            "name": self.name,
            "status": self.status,
        }
        if self.description:
            hsh["description"] = self.description
        return hsh

    def to_full_dict(self):
        return {
            "domainInfo": self.to_short_dict(),
            "configuration": {
                "workflowExecutionRetentionPeriodInDays": self.retention,
            }
        }

    def get_type(self, kind, name, version, ignore_empty=False):
        try:
            return self.types[kind][name][version]
        except KeyError:
            if not ignore_empty:
                raise SWFUnknownResourceFault(
                    "type",
                    "{}Type=[name={}, version={}]".format(
                        kind.capitalize(), name, version
                    )
                )

    def add_type(self, _type):
        self.types[_type.kind][_type.name][_type.version] = _type

    def find_types(self, kind, status):
        _all = []
        for _, family in self.types[kind].iteritems():
            for _, _type in family.iteritems():
                if _type.status == status:
                    _all.append(_type)
        return _all

    def add_workflow_execution(self, workflow_execution):
        _id = workflow_execution.workflow_id
        if self.workflow_executions.get(_id):
            raise SWFWorkflowExecutionAlreadyStartedFault()
        self.workflow_executions[_id] = workflow_execution

    def get_workflow_execution(self, run_id, workflow_id):
        wfe = self.workflow_executions.get(workflow_id)
        if not wfe or wfe.run_id != run_id:
            raise SWFUnknownResourceFault(
                "execution",
                "WorkflowExecution=[workflowId={}, runId={}]".format(
                    workflow_id, run_id
                )
            )
        return wfe

    def add_to_task_list(self, task_list, obj):
        self.task_lists[task_list].append(obj)
