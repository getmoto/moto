from __future__ import unicode_literals
from collections import defaultdict
import uuid

import boto.swf

from moto.core import BaseBackend
from moto.core.utils import camelcase_to_underscores

from .exceptions import (
    SWFUnknownResourceFault,
    SWFDomainAlreadyExistsFault,
    SWFDomainDeprecatedFault,
    SWFSerializationException,
    SWFTypeAlreadyExistsFault,
    SWFTypeDeprecatedFault,
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

    def add_workflow_execution(self, workflow_execution_id, workflow_execution):
        if self.workflow_executions.get(workflow_execution_id):
            raise SWFWorkflowExecutionAlreadyStartedFault()
        self.workflow_executions[workflow_execution_id] = workflow_execution


class GenericType(object):
    def __init__(self, name, version, **kwargs):
        self.name = name
        self.version = version
        self.status = "REGISTERED"
        if "description" in kwargs:
            self.description = kwargs.pop("description")
        for key, value in kwargs.iteritems():
            self.__setattr__(key, value)

    def __repr__(self):
        cls = self.__class__.__name__
        attrs = "name: %(name)s, version: %(version)s, status: %(status)s" % self.__dict__
        return "{}({})".format(cls, attrs)

    @property
    def kind(self):
        raise NotImplementedError()

    @property
    def _configuration_keys(self):
        raise NotImplementedError()

    def to_short_dict(self):
        return {
            "name": self.name,
            "version": self.version,
        }

    def to_medium_dict(self):
        hsh = {
            "{}Type".format(self.kind): self.to_short_dict(),
            "creationDate": 1420066800,
            "status": self.status,
        }
        if self.status == "DEPRECATED":
            hsh["deprecationDate"] = 1422745200
        if hasattr(self, "description"):
            hsh["description"] = self.description
        return hsh

    def to_full_dict(self):
        hsh = {
            "typeInfo": self.to_medium_dict(),
            "configuration": {}
        }
        if hasattr(self, "task_list"):
            hsh["configuration"]["defaultTaskList"] = {"name": self.task_list}
        for key in self._configuration_keys:
            attr = camelcase_to_underscores(key)
            if not hasattr(self, attr):
                continue
            if not getattr(self, attr):
                continue
            hsh["configuration"][key] = getattr(self, attr)
        return hsh


class ActivityType(GenericType):
    @property
    def _configuration_keys(self):
        return [
            "defaultTaskHeartbeatTimeout",
            "defaultTaskScheduleToCloseTimeout",
            "defaultTaskScheduleToStartTimeout",
            "defaultTaskStartToCloseTimeout",
        ]

    @property
    def kind(self):
        return "activity"


class WorkflowType(GenericType):
    @property
    def _configuration_keys(self):
        return [
            "defaultChildPolicy",
            "defaultExecutionStartToCloseTimeout",
            "defaultTaskStartToCloseTimeout",
        ]

    @property
    def kind(self):
        return "workflow"


class WorkflowExecution(object):
    def __init__(self, workflow_type, **kwargs):
        self.workflow_type = workflow_type
        self.run_id = uuid.uuid4().hex
        for key, value in kwargs.iteritems():
            self.__setattr__(key, value)

    def __repr__(self):
        return "WorkflowExecution(run_id: {})".format(self.run_id)


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

    # TODO: find what triggers a "DefaultUndefinedFault" and implement it
    # (didn't found in boto source code, nor in the docs, nor on a Google search)
    # (will try to reach support)
    def start_workflow_execution(self, domain_name, workflow_execution_id,
                                 workflow_name, workflow_version,
                                 tag_list=None, **kwargs):
        self._check_string(domain_name)
        self._check_string(workflow_execution_id)
        self._check_string(workflow_name)
        self._check_string(workflow_version)
        self._check_none_or_list_of_strings(tag_list)
        for _, value in kwargs.iteritems():
            self._check_none_or_string(value)

        domain = self._get_domain(domain_name)
        wf_type = domain.get_type("workflow", workflow_name, workflow_version)
        if wf_type.status == "DEPRECATED":
            raise SWFTypeDeprecatedFault(wf_type)
        wfe = WorkflowExecution(wf_type, tag_list=tag_list, **kwargs)
        domain.add_workflow_execution(workflow_execution_id, wfe)

        return wfe


swf_backends = {}
for region in boto.swf.regions():
    swf_backends[region.name] = SWFBackend(region.name)
