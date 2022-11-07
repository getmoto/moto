"""SimpleDBBackend class with methods for supported APIs."""
import re
from collections import defaultdict
from moto.core import BaseBackend, BackendDict, BaseModel
from threading import Lock

from .exceptions import InvalidDomainName, UnknownDomainName


class FakeItem(BaseModel):
    def __init__(self):
        self.attributes = []
        self.lock = Lock()

    def get_attributes(self, names):
        if not names:
            return self.attributes
        return [attr for attr in self.attributes if attr["name"] in names]

    def put_attributes(self, attributes):
        # Replacing attributes involves quite a few loops
        # Lock this, so we know noone else touches this list while we're operating on it
        with self.lock:
            for attr in attributes:
                if attr.get("replace", "false").lower() == "true":
                    self._remove_attributes(attr["name"])
                self.attributes.append(attr)

    def _remove_attributes(self, name):
        self.attributes = [attr for attr in self.attributes if attr["name"] != name]


class FakeDomain(BaseModel):
    def __init__(self, name):
        self.name = name
        self.items = defaultdict(FakeItem)

    def get(self, item_name, attribute_names):
        item = self.items[item_name]
        return item.get_attributes(attribute_names)

    def put(self, item_name, attributes):
        item = self.items[item_name]
        item.put_attributes(attributes)


class SimpleDBBackend(BaseBackend):
    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)
        self.domains = dict()

    def create_domain(self, domain_name):
        self._validate_domain_name(domain_name)
        self.domains[domain_name] = FakeDomain(name=domain_name)

    def list_domains(self):
        """
        The `max_number_of_domains` and `next_token` parameter have not been implemented yet - we simply return all domains.
        """
        return self.domains.keys()

    def delete_domain(self, domain_name):
        self._validate_domain_name(domain_name)
        # Ignore unknown domains - AWS does the same
        self.domains.pop(domain_name, None)

    def _validate_domain_name(self, domain_name):
        # Domain Name needs to have at least 3 chars
        # Can only contain characters: a-z, A-Z, 0-9, '_', '-', and '.'
        if not re.match("^[a-zA-Z0-9-_.]{3,}$", domain_name):
            raise InvalidDomainName(domain_name)

    def _get_domain(self, domain_name):
        if domain_name not in self.domains:
            raise UnknownDomainName()
        return self.domains[domain_name]

    def get_attributes(self, domain_name, item_name, attribute_names):
        """
        Behaviour for the consistent_read-attribute is not yet implemented
        """
        self._validate_domain_name(domain_name)
        domain = self._get_domain(domain_name)
        return domain.get(item_name, attribute_names)

    def put_attributes(self, domain_name, item_name, attributes):
        """
        Behaviour for the expected-attribute is not yet implemented.
        """
        self._validate_domain_name(domain_name)
        domain = self._get_domain(domain_name)
        domain.put(item_name, attributes)


sdb_backends = BackendDict(SimpleDBBackend, "sdb")
