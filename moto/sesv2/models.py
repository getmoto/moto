"""SESV2Backend class with methods for supported APIs."""

from moto.core import BackendDict
from ..ses.models import SESBackend


class SESV2Backend(SESBackend):
    """Implementation of SESV2 APIs, piggy back on v1 SES"""

    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)


sesv2_backends = BackendDict(SESV2Backend, "sesv2")
