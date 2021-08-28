from __future__ import unicode_literals
from collections import defaultdict

from moto.core import ACCOUNT_ID, BaseModel
from ..exceptions import (
    SWFUnknownResourceFault,
    SWFWorkflowExecutionAlreadyStartedFault,
)


class Domain(BaseModel):
    def __init__(self, name, retention, region_name, description=None):
        self.name = name
        self.retention = retention
        self.region_name = region_name
        self.description = description
        self.status = "REGISTERED"
        self.types = {"activity": defaultdict(dict), "workflow": defaultdict(dict)}
        # Workflow executions have an id, which unicity is guaranteed
        # at domain level (not super clear in the docs, but I checked
        # that against SWF API) ; hence the storage method as a dict
        # of "workflow_id (client determined)" => WorkflowExecution()
        # here.
        self.workflow_executions = []
        self.activity_task_lists = {}
        self.decision_task_lists = {}

    def __repr__(self):
        return "Domain(name: %(name)s, status: %(status)s)" % self.__dict__

    def to_short_dict(self):
        hsh = {"name": self.name, "status": self.status}
        if self.description:
            hsh["description"] = self.description
        hsh["arn"] = "arn:aws:swf:{0}:{1}:/domain/{2}".format(
            self.region_name, ACCOUNT_ID, self.name
        )
        return hsh

    def to_full_dict(self):
        return {
            "domainInfo": self.to_short_dict(),
            "configuration": {"workflowExecutionRetentionPeriodInDays": self.retention},
        }

    def get_type(self, kind, name, version, ignore_empty=False):
        try:
            return self.types[kind][name][version]
        except KeyError:
            if not ignore_empty:
                raise SWFUnknownResourceFault(
                    "type",
                    "{0}Type=[name={1}, version={2}]".format(
                        kind.capitalize(), name, version
                    ),
                )

    def add_type(self, _type):
        self.types[_type.kind][_type.name][_type.version] = _type

    def find_types(self, kind, status):
        _all = []
        for family in self.types[kind].values():
            for _type in family.values():
                if _type.status == status:
                    _all.append(_type)
        return _all

    def add_workflow_execution(self, workflow_execution):
        _id = workflow_execution.workflow_id
        if self.get_workflow_execution(_id, raise_if_none=False):
            raise SWFWorkflowExecutionAlreadyStartedFault()
        self.workflow_executions.append(workflow_execution)

    def get_workflow_execution(
        self, workflow_id, run_id=None, raise_if_none=True, raise_if_closed=False
    ):
        # query
        if run_id:
            _all = [
                w
                for w in self.workflow_executions
                if w.workflow_id == workflow_id and w.run_id == run_id
            ]
        else:
            _all = [
                w
                for w in self.workflow_executions
                if w.workflow_id == workflow_id and w.open
            ]
        # reduce
        wfe = _all[0] if _all else None
        # raise if closed / none
        if raise_if_closed and wfe and wfe.execution_status == "CLOSED":
            wfe = None
        if not wfe and raise_if_none:
            if run_id:
                args = [
                    "execution",
                    "WorkflowExecution=[workflowId={0}, runId={1}]".format(
                        workflow_id, run_id
                    ),
                ]
            else:
                args = ["execution, workflowId = {0}".format(workflow_id)]
            raise SWFUnknownResourceFault(*args)
        # at last return workflow execution
        return wfe

    def add_to_activity_task_list(self, task_list, obj):
        if task_list not in self.activity_task_lists:
            self.activity_task_lists[task_list] = []
        self.activity_task_lists[task_list].append(obj)

    @property
    def activity_tasks(self):
        _all = []
        for tasks in self.activity_task_lists.values():
            _all += tasks
        return _all

    def add_to_decision_task_list(self, task_list, obj):
        if task_list not in self.decision_task_lists:
            self.decision_task_lists[task_list] = []
        self.decision_task_lists[task_list].append(obj)

    @property
    def decision_tasks(self):
        _all = []
        for tasks in self.decision_task_lists.values():
            _all += tasks
        return _all
