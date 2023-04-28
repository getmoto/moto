"""Handles incoming sesv2 requests, invokes methods, returns responses."""
import json

from moto.core.responses import BaseResponse
from .models import sesv2_backends
from ..ses.responses import SEND_EMAIL_RESPONSE
from .models import SESV2Backend
from typing import List, Dict, Any


class SESV2Response(BaseResponse):
    """Handler for SESV2 requests and responses."""

    def __init__(self) -> None:
        super().__init__(service_name="sesv2")

    @property
    def sesv2_backend(self) -> SESV2Backend:
        """Return backend instance specific for this region."""
        return sesv2_backends[self.current_account][self.region]

    def send_email(self) -> str:
        """Piggy back on functionality from v1 mostly"""

        params = get_params_dict(self.querystring)
        from_email_address = params.get("FromEmailAddress")
        destination = params.get("Destination")
        content = params.get("Content")
        if "Raw" in content:
            all_destinations: List[str] = []
            if "ToAddresses" in destination:
                all_destinations = all_destinations + destination["ToAddresses"]
            if "CcAddresses" in destination:
                all_destinations = all_destinations + destination["CcAddresses"]
            if "BccAddresses" in destination:
                all_destinations = all_destinations + destination["BccAddresses"]
            message = self.sesv2_backend.send_raw_email(
                source=from_email_address,
                destinations=all_destinations,
                raw_data=content["Raw"]["Data"],
            )
        elif "Simple" in content:
            message = self.sesv2_backend.send_email(  # type: ignore
                source=from_email_address,
                destinations=destination,
                subject=content["Simple"]["Subject"]["Data"],
                body=content["Simple"]["Subject"]["Data"],
            )
        elif "Template" in content:
            raise NotImplementedError("Template functionality not ready")

        # use v1 templates as response same in v1 and v2
        template = self.response_template(SEND_EMAIL_RESPONSE)
        return template.render(message=message)

    def list_contacts(self) -> str:
        name = self._get_param("ContactListName")
        contacts = self.sesv2_backend.list_contacts(name)
        return json.dumps(dict(Contacts=[c.response_object for c in contacts]))

    def create_contact(self) -> str:
        # parsing of these params is nasty, hopefully there is a tidier way
        name = self._get_param("ContactListName")
        params = get_params_dict(self.data)
        self.sesv2_backend.create_contact(name, params)
        return json.dumps({})


def get_params_dict(odict: Dict[str, Any]) -> Any:
    # parsing of these params is nasty, hopefully there is a tidier way
    return json.loads(list(dict(odict.items()).keys())[0])
