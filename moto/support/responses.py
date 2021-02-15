from __future__ import unicode_literals
from moto.core.responses import BaseResponse
from .models import support_backends
import json


class SupportResponse(BaseResponse):
    SERVICE_NAME = "support"

    @property
    def support_backend(self):
        return support_backends[self.region]

    def describe_trusted_advisor_checks(self):
        language = self._get_param("language")
        checks = self.support_backend.describe_trusted_advisor_checks(
            language=language,
        )

        return json.dumps({"checks": checks})
