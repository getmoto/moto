"""Handles incoming sesv2 requests, invokes methods, returns responses."""
import json

from moto.core.responses import BaseResponse
from .models import sesv2_backends
from ..ses.responses import SEND_EMAIL_RESPONSE
from .models import SESV2Backend


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

        # parsing of these params is nasty, hopefully there is a tidier way
        params = json.loads(list(dict(self.querystring.items()).keys())[0])
        from_email_address = params.get("FromEmailAddress")
        destination = params.get("Destination")
        content = params.get("Content")

        message = self.sesv2_backend.send_email(
            source=from_email_address,
            destinations=destination,
            subject=content["Simple"]["Subject"]["Data"],
            body=content["Simple"]["Subject"]["Data"],
        )

        # use v1 templates as response same in v1 and v2
        template = self.response_template(SEND_EMAIL_RESPONSE)
        return template.render(message=message)
