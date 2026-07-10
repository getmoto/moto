"""Handles incoming paymentcryptography requests, invokes methods, returns responses."""
import json

from moto.core.responses import BaseResponse
from .models import paymentcryptography_backends


class PaymentCryptographyControlPlaneResponse(BaseResponse):
    """Handler for PaymentCryptographyControlPlane requests and responses."""

    def __init__(self):
        super().__init__(service_name="paymentcryptography")

    @property
    def paymentcryptography_backend(self):
        """Return backend instance specific for this region."""
        # TODO
        # paymentcryptography_backends is not yet typed
        # Please modify moto/backends.py to add the appropriate type annotations for this service
        return paymentcryptography_backends[self.current_account][self.region]

    # add methods from here


# add templates from here
