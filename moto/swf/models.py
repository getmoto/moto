from __future__ import unicode_literals

import boto.swf

from moto.core import BaseBackend
from .exceptions import (
    SWFUnknownResourceFault,
    SWFDomainAlreadyExistsFault,
    SWFDomainDeprecatedFault,
)


class Domain(object):
    def __init__(self, name, retention, description=None):
        self.name = name
        self.retention = retention
        self.description = description
        self.status = "REGISTERED"

    def __repr__(self):
        return "Domain(name: %s, retention: %s, description: %s)" % (self.name, self.retention, self.description)


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

    def list_domains(self, status):
        return [domain for domain in self.domains
                if domain.status == status]

    def register_domain(self, name, workflow_execution_retention_period_in_days,
                        description=None):
        if self._get_domain(name, ignore_empty=True):
            raise SWFDomainAlreadyExistsFault(name)
        domain = Domain(name, workflow_execution_retention_period_in_days,
                        description)
        self.domains.append(domain)

    def deprecate_domain(self, name):
        domain = self._get_domain(name)
        if domain.status == "DEPRECATED":
            raise SWFDomainDeprecatedFault(name)
        domain.status = "DEPRECATED"

    def describe_domain(self, name):
        return self._get_domain(name)


swf_backends = {}
for region in boto.swf.regions():
    swf_backends[region.name] = SWFBackend(region.name)
