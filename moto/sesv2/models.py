"""SESV2Backend class with methods for supported APIs."""

from moto.core import BackendDict, BaseBackend, BaseModel
from ..ses.models import ses_backends, Message, RawMessage
from typing import Dict, List


class ContactList(BaseModel):
    def __init__(
        self,
        name: str,
        email_address: str,
        topic_default_preferences: List[Dict[str, str]],
        topic_preferences: List[Dict[str, str]],
        unsubscribe_all: bool,
    ):
        self.name = name
        self.email_address = email_address
        self.topic_default_preferences = topic_default_preferences
        self.topic_preferences = topic_preferences
        self.unsubscribe_all = unsubscribe_all


class SESV2Backend(BaseBackend):
    """Implementation of SESV2 APIs, piggy back on v1 SES"""

    def __init__(self, region_name: str, account_id: str):
        super().__init__(region_name, account_id)
        self.contacs: List[ContactList] = []

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

    def list_contacts(self, name: str) -> List[ContactList]:
        return [x for x in self.contacs if x.name == name]


sesv2_backends = BackendDict(SESV2Backend, "sesv2")
