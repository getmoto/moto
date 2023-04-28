"""SESV2Backend class with methods for supported APIs."""

from moto.core import BackendDict, BaseBackend, BaseModel
from ..ses.models import ses_backends, Message, RawMessage
from typing import Dict, List


class Contact(BaseModel):
    def __init__(
        self,
        ContactListName: str,
        EmailAddress: str,
        TopicPreferences: List[Dict[str, str]],
        TopicDefaultPreferences: List[Dict[str, str]],
        UnsubscribeAll: bool,
    ) -> None:
        self.ContactListName = ContactListName
        self.EmailAddress = EmailAddress
        self.TopicDefaultPreferences = TopicDefaultPreferences
        self.TopicPreferences = TopicPreferences
        self.UnsubscribeAll = UnsubscribeAll


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
        return [x.__dict__ for x in self.contacs if x.ContactListName == name]

    def create_contact(self, name: str, params: dict) -> dict:
        new_contact = Contact(ContactListName=name, **params)
        self.contacs.append(new_contact)
        return {}


sesv2_backends = BackendDict(SESV2Backend, "sesv2")
