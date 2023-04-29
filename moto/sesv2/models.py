"""SESV2Backend class with methods for supported APIs."""

from moto.core import BackendDict, BaseBackend, BaseModel
from ..ses.models import ses_backends, Message, RawMessage
from moto.core.utils import unix_time
from typing import Dict, List, Any
from .exceptions import NotFoundException


class Contact(BaseModel):
    def __init__(
        self,
        contact_list_name: str,
        email_address: str,
        topic_preferences: List[Dict[str, str]],
        unsubscribe_all: bool,
    ) -> None:
        self.contact_list_name = contact_list_name
        self.email_address = email_address
        self.topic_default_preferences: List[Dict[str, str]] = []
        self.topic_preferences = topic_preferences
        self.unsubscribe_all = unsubscribe_all

    @property
    def response_object(self) -> Dict[str, Any]:  # type: ignore[misc]
        return {
            "ContactListName": self.contact_list_name,
            "EmailAddress": self.email_address,
            "TopicDefaultPreferences": self.topic_default_preferences,
            "TopicPreferences": self.topic_preferences,
            "UnsubscribeAll": self.unsubscribe_all,
        }


class ContactList(BaseModel):
    def __init__(
        self,
        contact_list_name: str,
        description: str,
        topics: List[Dict[str, str]],
    ) -> None:
        self.contact_list_name = contact_list_name
        self.description = description
        self.topics = topics
        self.last_updated = unix_time()

    @property
    def response_object(self) -> Dict[str, Any]:  # type: ignore[misc]
        return {
            "ContactListName": self.contact_list_name,
            "LastUpdatedTimestamp": self.last_updated,
        }


class SESV2Backend(BaseBackend):
    """Implementation of SESV2 APIs, piggy back on v1 SES"""

    def __init__(self, region_name: str, account_id: str):
        super().__init__(region_name, account_id)
        self.contacts: List[Contact] = []
        self.contacts_lists: List[ContactList] = []

    def delete_contact_list(self, name: str) -> None:
        to_delete = next(
            (
                contact_list
                for contact_list in self.contacts_lists
                if contact_list.contact_list_name == name
            ),
            None,
        )
        if to_delete:
            self.contacts_lists.remove(to_delete)
        else:
            raise NotFoundException(f"List with name: {name} doesn't exist")

    def delete_contact(self, email: str) -> None:
        to_delete = next(
            (contact for contact in self.contacts if contact.email_address == email),
            None,
        )
        if to_delete:
            self.contacts.remove(to_delete)
        else:
            raise NotFoundException(f"Contact with name: {email} doesn't exist")

    def list_contact_lists(self) -> List[ContactList]:
        return self.contacts_lists

    def list_contacts(self, name: str) -> List[Contact]:
        return [x for x in self.contacts if x.contact_list_name == name]

    def create_contact(self, contact_list_name: str, params: Dict[str, Any]) -> None:
        email_address = params["EmailAddress"]
        topic_preferences = (
            [] if "TopicPreferences" not in params else params["TopicPreferences"]
        )
        unsubscribe_all = (
            False if "UnsubscribeAll" not in params else params["UnsubscribeAll"]
        )
        new_contact = Contact(
            contact_list_name, email_address, topic_preferences, unsubscribe_all
        )
        self.contacts.append(new_contact)

    def create_contact_list(self, params: Dict[str, Any]) -> None:
        name = params["ContactListName"]
        description = params.get("Description")
        topics = [] if "Topics" not in params else params["Topics"]
        new_list = ContactList(name, str(description), topics)
        self.contacts_lists.append(new_list)

    def send_email(
        self, source: str, destinations: Dict[str, List[str]], subject: str, body: str
    ) -> Message:
        v1_backend = ses_backends[self.account_id][self.region_name]
        message = v1_backend.send_email(
            source=source,
            destinations=destinations,
            subject=subject,
            body=body,
        )
        return message

    def send_raw_email(
        self, source: str, destinations: List[str], raw_data: str
    ) -> RawMessage:
        v1_backend = ses_backends[self.account_id][self.region_name]
        message = v1_backend.send_raw_email(
            source=source, destinations=destinations, raw_data=raw_data
        )
        return message


sesv2_backends = BackendDict(SESV2Backend, "sesv2")
