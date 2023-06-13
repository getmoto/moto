"""Handles incoming sesv2 requests, invokes methods, returns responses."""
import json

from moto.core.responses import AWSServiceSpec
from moto.core.responses import BaseResponse
from .models import sesv2_backends
from ..ses.responses import SEND_EMAIL_RESPONSE
from .models import SESV2Backend
from typing import List, Dict, Any
from urllib.parse import unquote


class SESV2Response(BaseResponse):
    """Handler for SESV2 requests and responses."""

    aws_service_spec = AWSServiceSpec("data/sesv2/2019-09-27/service-2.json")

    def __init__(self) -> None:
        super().__init__(service_name="sesv2")

    @property
    def sesv2_backend(self) -> SESV2Backend:
        """Return backend instance specific for this region."""
        return sesv2_backends[self.current_account][self.region]

    def send_email(self) -> str:
        """Piggy back on functionality from v1 mostly"""

        from_email_address = self._get_param("FromEmailAddress")
        if "Content.Raw.Data" in self.data:
            message = self.sesv2_backend.send_raw_email(
                source=from_email_address,
                destinations=[],
                raw_data=self._get_param("Content.Raw.Data"),
            )
        elif "Content.Simple.Subject.Data" in self.data:
            destinations: Dict[str, List[str]] = {
                "ToAddresses": [],
                "CcAddresses": [],
                "BccAddresses": [],
            }
            # no limit for recipients in v2
            for dest_type in destinations:
                i = 1
                while True:
                    field = f"Destination.{dest_type}.member.{i}"
                    address = self.querystring.get(field)
                    if address is None:
                        break
                    destinations[dest_type].append(address[0])
                    i += 1
            message = self.sesv2_backend.send_email(  # type: ignore
                source=from_email_address,
                destinations=destinations,
                subject=self._get_param("Content.Simple.Subject.Data"),
                body=self._get_param("Content.Simple.Body.Data"),
            )
        elif "Template" in self.data:
            raise NotImplementedError("Template functionality not ready")

        # use v1 templates as response same in v1 and v2
        template = self.response_template(SEND_EMAIL_RESPONSE)
        return template.render(message=message)

    def create_contact_list(self) -> str:
        params = self.get_params_dict(self.data)
        self.sesv2_backend.create_contact_list(params)
        return json.dumps({})

    def get_contact_list(self) -> str:
        contact_list_name = self._get_param("ContactListName")
        contact_list = self.sesv2_backend.get_contact_list(contact_list_name)
        return json.dumps(contact_list.response_object)

    def list_contact_lists(self) -> str:
        contact_lists = self.sesv2_backend.list_contact_lists()
        return json.dumps(dict(ContactLists=[c.response_object for c in contact_lists]))

    def delete_contact_list(self) -> str:
        name = self._get_param("ContactListName")
        self.sesv2_backend.delete_contact_list(name)
        return json.dumps({})

    def create_contact(self) -> str:
        contact_list_name = self._get_param("ContactListName")
        params = self.get_params_dict(self.data)
        self.sesv2_backend.create_contact(contact_list_name, params)
        return json.dumps({})

    def get_contact(self) -> str:
        email = unquote(self._get_param("EmailAddress"))
        contact_list_name = self._get_param("ContactListName")
        contact = self.sesv2_backend.get_contact(email, contact_list_name)
        return json.dumps(contact.response_object)

    def list_contacts(self) -> str:
        contact_list_name = self._get_param("ContactListName")
        contacts = self.sesv2_backend.list_contacts(contact_list_name)
        return json.dumps(dict(Contacts=[c.response_object for c in contacts]))

    def delete_contact(self) -> str:
        email = self._get_param("EmailAddress")
        contact_list_name = self._get_param("ContactListName")
        self.sesv2_backend.delete_contact(unquote(email), contact_list_name)
        return json.dumps({})

    def get_params_dict(self, odict: Dict[str, Any]) -> Dict[str, Any]:
        return {k: self._get_param(k) for k in odict.keys()}
