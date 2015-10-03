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
)
from .activity_type import ActivityType
from .domain import Domain
from .generic_type import GenericType
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

    # TODO: find what triggers a "DefaultUndefinedFault" and implement it
    # (didn't found in boto source code, nor in the docs, nor on a Google search)
    # (will try to reach support)
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
        wfe = WorkflowExecution(wf_type, workflow_id,
                                tag_list=tag_list, **kwargs)
        domain.add_workflow_execution(wfe)

        return wfe

    def describe_workflow_execution(self, domain_name, run_id, workflow_id):
        self._check_string(domain_name)
        self._check_string(run_id)
        self._check_string(workflow_id)
        domain = self._get_domain(domain_name)
        return domain.get_workflow_execution(run_id, workflow_id)


swf_backends = {}
for region in boto.swf.regions():
    swf_backends[region.name] = SWFBackend(region.name)
