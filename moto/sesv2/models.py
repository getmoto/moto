"""SESV2Backend class with methods for supported APIs."""

from moto.core import BackendDict, BaseBackend, BaseModel
from ..ses.models import ses_backends, Message, RawMessage
from typing import Dict, List, Optional, Any


class Contact(BaseModel):
    def __init__(
        self,
        contact_list_name: str,
        email_address: str,
        topic_preferences: Optional[Any],
        unsubscribe_all: Optional[bool],
    ) -> None:
        self.contact_list_name = contact_list_name
        self.email_address = email_address
        self.topic_default_preferences = [Dict[str, str]]
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


class SESV2Backend(BaseBackend):
    """Implementation of SESV2 APIs, piggy back on v1 SES"""

    def __init__(self, region_name: str, account_id: str):
        super().__init__(region_name, account_id)
        self.contacs: List[Contact] = []

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

    def list_contacts(self, name: str) -> List[Dict[str, Dict]]:
        return [x.response_object for x in self.contacs if x.contact_list_name == name]

    def create_contact(self, contact_list_name: str, params: dict) -> dict:
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
        self.contacs.append(new_contact)
        return {}


sesv2_backends = BackendDict(SESV2Backend, "sesv2")
