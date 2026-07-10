"""PaymentCryptographyControlPlaneBackend class with methods for supported APIs."""

from moto.core.base_backend import BaseBackend, BackendDict
from moto.core.common_models import BaseModel


class PaymentCryptographyControlPlaneBackend(BaseBackend):
    """Implementation of PaymentCryptographyControlPlane APIs."""

    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)

    # add methods from here


paymentcryptography_backends = BackendDict(PaymentCryptographyControlPlaneBackend, "payment-cryptography")