"""SESV2Backend class with methods for supported APIs."""

from typing import Any, Dict, List, Optional

from moto.core.base_backend import BackendDict, BaseBackend
from moto.utilities.paginator import paginate

from ..ses.exceptions import NotFoundException
from ..ses.models import (
    ConfigurationSet,
    Contact,
    ContactList,
    DedicatedIpPool,
    EmailIdentity,
    Message,
    RawMessage,
    ses_backends,
)

PAGINATION_MODEL = {
    "list_dedicated_ip_pools": {
        "input_token": "next_token",
        "limit_key": "page_size",
        "limit_default": 100,
        "unique_attribute": ["pool_name"],
    },
    "list_email_identities": {
        "input_token": "next_token",
        "limit_key": "page_size",
        "limit_default": 100,
        "unique_attribute": "IdentityName",
    },
    "list_configuration_sets": {
        "input_token": "next_token",
        "limit_key": "page_size",
        "limit_default": 100,
        "unique_attribute": "configuration_set_name",
    },
}


class SESV2Backend(BaseBackend):
    """Implementation of SESV2 APIs, piggy back on v1 SES"""

    def __init__(self, region_name: str, account_id: str):
        super().__init__(region_name, account_id)

        # Store local variables in v1 backend for interoperability
        self.core_backend = ses_backends[self.account_id][self.region_name]

    def create_contact_list(self, params: Dict[str, Any]) -> None:
        name = params["ContactListName"]
        description = params.get("Description")
        topics = [] if "Topics" not in params else params["Topics"]
        new_list = ContactList(name, str(description), topics)
        self.core_backend.contacts_lists[name] = new_list

    def get_contact_list(self, contact_list_name: str) -> ContactList:
        if contact_list_name in self.core_backend.contacts_lists:
            return self.core_backend.contacts_lists[contact_list_name]
        else:
            raise NotFoundException(
                f"List with name: {contact_list_name} doesn't exist."
            )

    def list_contact_lists(self) -> List[ContactList]:
        return self.core_backend.contacts_lists.values()  # type: ignore[return-value]

    def delete_contact_list(self, name: str) -> None:
        if name in self.core_backend.contacts_lists:
            del self.core_backend.contacts_lists[name]
        else:
            raise NotFoundException(f"List with name: {name} doesn't exist")

    def create_contact(self, contact_list_name: str, params: Dict[str, Any]) -> None:
        contact_list = self.get_contact_list(contact_list_name)
        contact_list.create_contact(contact_list_name, params)
        return

    def get_contact(self, email: str, contact_list_name: str) -> Contact:
        contact_list = self.get_contact_list(contact_list_name)
        contact = contact_list.get_contact(email)
        return contact

    def list_contacts(self, contact_list_name: str) -> List[Contact]:
        contact_list = self.get_contact_list(contact_list_name)
        contacts = contact_list.list_contacts()
        return contacts

    def delete_contact(self, email: str, contact_list_name: str) -> None:
        contact_list = self.get_contact_list(contact_list_name)
        contact_list.delete_contact(email)
        return

    def send_email(
        self, source: str, destinations: Dict[str, List[str]], subject: str, body: str
    ) -> Message:
        message = self.core_backend.send_email(
            source=source,
            destinations=destinations,
            subject=subject,
            body=body,
        )
        return message

    def send_raw_email(
        self, source: str, destinations: List[str], raw_data: str
    ) -> RawMessage:
        message = self.core_backend.send_raw_email(
            source=source, destinations=destinations, raw_data=raw_data
        )
        return message

    def create_email_identity(
        self,
        email_identity: str,
        tags: Optional[Dict[str, str]],
        dkim_signing_attributes: Optional[object],
        configuration_set_name: Optional[str],
    ) -> EmailIdentity:
        return self.core_backend.create_email_identity_v2(
            email_identity, tags, dkim_signing_attributes, configuration_set_name
        )

    def delete_email_identity(
        self,
        email_identity: str,
    ) -> None:
        self.core_backend.delete_identity(email_identity)

    @paginate(pagination_model=PAGINATION_MODEL)
    def list_email_identities(self) -> List[EmailIdentity]:
        identities = list(self.core_backend.email_identities.values())
        return identities

    def create_configuration_set(
        self,
        configuration_set_name: str,
        tracking_options: Dict[str, str],
        delivery_options: Dict[str, Any],
        reputation_options: Dict[str, Any],
        sending_options: Dict[str, bool],
        tags: List[Dict[str, str]],
        suppression_options: Dict[str, List[str]],
        vdm_options: Dict[str, Dict[str, str]],
    ) -> None:
        self.core_backend.create_configuration_set_v2(
            configuration_set_name=configuration_set_name,
            tracking_options=tracking_options,
            delivery_options=delivery_options,
            reputation_options=reputation_options,
            sending_options=sending_options,
            tags=tags,
            suppression_options=suppression_options,
            vdm_options=vdm_options,
        )

    def delete_configuration_set(self, configuration_set_name: str) -> None:
        self.core_backend.delete_configuration_set(configuration_set_name)

    def get_configuration_set(self, configuration_set_name: str) -> ConfigurationSet:
        config_set = self.core_backend.describe_configuration_set(
            configuration_set_name=configuration_set_name
        )
        return config_set

    @paginate(pagination_model=PAGINATION_MODEL)
    def list_configuration_sets(self) -> List[ConfigurationSet]:
        return self.core_backend._list_all_configuration_sets()

    def create_dedicated_ip_pool(
        self, pool_name: str, tags: List[Dict[str, str]], scaling_mode: str
    ) -> None:
        if pool_name not in self.core_backend.dedicated_ip_pools:
            new_pool = DedicatedIpPool(
                pool_name=pool_name, tags=tags, scaling_mode=scaling_mode
            )
            self.core_backend.dedicated_ip_pools[pool_name] = new_pool

    def delete_dedicated_ip_pool(self, pool_name: str) -> None:
        self.core_backend.dedicated_ip_pools.pop(pool_name)

    @paginate(pagination_model=PAGINATION_MODEL)
    def list_dedicated_ip_pools(self) -> List[str]:
        return list(self.core_backend.dedicated_ip_pools.keys())

    def get_dedicated_ip_pool(self, pool_name: str) -> DedicatedIpPool:
        if not self.core_backend.dedicated_ip_pools.get(pool_name, None):
            raise NotFoundException(pool_name)
        return self.core_backend.dedicated_ip_pools[pool_name]

    def get_email_identity(self, email_identity: str) -> EmailIdentity:
        if email_identity not in self.core_backend.email_identities:
            raise NotFoundException(email_identity)
        return self.core_backend.email_identities[email_identity]

    def create_email_identity_policy(
        self, email_identity: str, policy_name: str, policy: str
    ) -> None:
        email_id = self.get_email_identity(email_identity)

        email_id.policies[policy_name] = policy

        return

    def delete_email_identity_policy(
        self, email_identity: str, policy_name: str
    ) -> None:
        if email_identity not in self.core_backend.email_identities:
            raise NotFoundException(email_identity)

        email_id = self.core_backend.email_identities[email_identity]

        if policy_name in email_id.policies:
            del email_id.policies[policy_name]

        return

    def update_email_identity_policy(
        self, email_identity: str, policy_name: str, policy: str
    ) -> None:
        if email_identity not in self.core_backend.email_identities:
            raise NotFoundException(email_identity)

        email_id = self.core_backend.email_identities[email_identity]

        email_id.policies[policy_name] = policy

        return

    def get_email_identity_policies(self, email_identity: str) -> Dict[str, Any]:
        email_id = self.get_email_identity(email_identity)

        return email_id.policies


sesv2_backends = BackendDict(SESV2Backend, "sesv2")
