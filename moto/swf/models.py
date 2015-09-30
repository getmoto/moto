from __future__ import unicode_literals
from collections import defaultdict

import boto.swf

from moto.core import BaseBackend
from .exceptions import (
    SWFUnknownResourceFault,
    SWFDomainAlreadyExistsFault,
    SWFDomainDeprecatedFault,
    SWFSerializationException,
    SWFTypeAlreadyExistsFault,
    SWFTypeDeprecatedFault,
)


class Domain(object):
    def __init__(self, name, retention, description=None):
        self.name = name
        self.retention = retention
        self.description = description
        self.status = "REGISTERED"
        self.activity_types = defaultdict(dict)
        self.workflow_types = defaultdict(dict)

    def __repr__(self):
        return "Domain(name: %(name)s, status: %(status)s)" % self.__dict__

    def get_activity_type(self, name, version, ignore_empty=False):
        try:
            return self.activity_types[name][version]
        except KeyError:
            if not ignore_empty:
                raise SWFUnknownResourceFault(
                    "type",
                    "ActivityType=[name={}, version={}]".format(name, version)
                )

    def add_activity_type(self, _type):
        self.activity_types[_type.name][_type.version] = _type

    def find_activity_types(self, status):
        _all = []
        for _, family in self.activity_types.iteritems():
            for _, _type in family.iteritems():
                if _type.status == status:
                    _all.append(_type)
        return _all

    # TODO: refactor it with get_activity_type()
    def get_workflow_type(self, name, version, ignore_empty=False):
        try:
            return self.workflow_types[name][version]
        except KeyError:
            if not ignore_empty:
                raise SWFUnknownResourceFault(
                    "type",
                    "WorkflowType=[name={}, version={}]".format(name, version)
                )

    # TODO: refactor it with add_activity_type()
    def add_workflow_type(self, _type):
        self.workflow_types[_type.name][_type.version] = _type

    # TODO: refactor it with find_activity_types()
    def find_workflow_types(self, status):
        _all = []
        for _, family in self.workflow_types.iteritems():
            for _, _type in family.iteritems():
                if _type.status == status:
                    _all.append(_type)
        return _all


class ActivityType(object):
    def __init__(self, name, version, **kwargs):
        self.name = name
        self.version = version
        self.status = "REGISTERED"
        for key, value in kwargs.iteritems():
            self.__setattr__(key, value)

    def __repr__(self):
        return "ActivityType(name: %(name)s, version: %(version)s)" % self.__dict__


class WorkflowType(object):
    def __init__(self, name, version, **kwargs):
        self.name = name
        self.version = version
        self.status = "REGISTERED"
        for key, value in kwargs.iteritems():
            self.__setattr__(key, value)

    def __repr__(self):
        return "WorkflowType(name: %(name)s, version: %(version)s)" % self.__dict__


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

    def _check_string(self, parameter):
        if not isinstance(parameter, basestring):
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
        if description:
            self._check_string(description)
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

    def list_activity_types(self, domain_name, status, reverse_order=None):
        self._check_string(domain_name)
        self._check_string(status)
        domain = self._get_domain(domain_name)
        _types = domain.find_activity_types(status)
        _types = sorted(_types, key=lambda domain: domain.name)
        if reverse_order:
            _types = reversed(_types)
        return _types

    def register_activity_type(self, domain_name, name, version, **kwargs):
        self._check_string(domain_name)
        self._check_string(name)
        self._check_string(version)
        for _, value in kwargs.iteritems():
            if value == (None,):
                print _
            if value is not None:
                self._check_string(value)
        domain = self._get_domain(domain_name)
        _type = domain.get_activity_type(name, version, ignore_empty=True)
        if _type:
            raise SWFTypeAlreadyExistsFault(_type)
        activity_type = ActivityType(name, version, **kwargs)
        domain.add_activity_type(activity_type)

    def deprecate_activity_type(self, domain_name, name, version):
        self._check_string(domain_name)
        self._check_string(name)
        self._check_string(version)
        domain = self._get_domain(domain_name)
        _type = domain.get_activity_type(name, version)
        if _type.status == "DEPRECATED":
            raise SWFTypeDeprecatedFault(_type)
        _type.status = "DEPRECATED"

    def describe_activity_type(self, domain_name, name, version):
        self._check_string(domain_name)
        self._check_string(name)
        self._check_string(version)
        domain = self._get_domain(domain_name)
        return domain.get_activity_type(name, version)

    def list_workflow_types(self, domain_name, status, reverse_order=None):
        self._check_string(domain_name)
        self._check_string(status)
        domain = self._get_domain(domain_name)
        _types = domain.find_workflow_types(status)
        _types = sorted(_types, key=lambda domain: domain.name)
        if reverse_order:
            _types = reversed(_types)
        return _types

    def register_workflow_type(self, domain_name, name, version, **kwargs):
        self._check_string(domain_name)
        self._check_string(name)
        self._check_string(version)
        for _, value in kwargs.iteritems():
            if value == (None,):
                print _
            if value is not None:
                self._check_string(value)
        domain = self._get_domain(domain_name)
        _type = domain.get_workflow_type(name, version, ignore_empty=True)
        if _type:
            raise SWFTypeAlreadyExistsFault(_type)
        workflow_type = WorkflowType(name, version, **kwargs)
        domain.add_workflow_type(workflow_type)

    def deprecate_workflow_type(self, domain_name, name, version):
        self._check_string(domain_name)
        self._check_string(name)
        self._check_string(version)
        domain = self._get_domain(domain_name)
        _type = domain.get_workflow_type(name, version)
        if _type.status == "DEPRECATED":
            raise SWFTypeDeprecatedFault(_type)
        _type.status = "DEPRECATED"

    def describe_workflow_type(self, domain_name, name, version):
        self._check_string(domain_name)
        self._check_string(name)
        self._check_string(version)
        domain = self._get_domain(domain_name)
        return domain.get_workflow_type(name, version)

swf_backends = {}
for region in boto.swf.regions():
    swf_backends[region.name] = SWFBackend(region.name)
