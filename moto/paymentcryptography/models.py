"""PaymentCryptographyControlPlaneBackend class with methods for supported APIs."""

import string
import random
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


from moto.core.base_backend import BaseBackend, BackendDict
from moto.core.common_models import BaseModel


def _random_key_id() -> str:
    chars = string.ascii_lowercase + string.digits
    return "".join(random.choices(chars, k=16))


def _key_check_value() -> str:
    # return a fake but plausible key check value based on the algorithm
    kcv = "".join(random.choices("0123456789ABCDEF", k=6))
    return kcv

class Key(BaseModel):
    def __init__(
        self,
        account_id: str,
        region_name: str,
        key_attributes: Optional[Dict[str, Any]],
        key_check_value_algorithm: str,
        exportable: bool,
        enabled: bool,
        tags: list[dict[str, str]],
        derive_key_usage: str,
        replication_regions: list[str]
    ):
        self.key_id = _random_key_id()
        self.key_arn = f"arn:aws:payment-cryptography:{region_name}:{account_id}:key/{self.key_id}"
        self.key_attributes = key_attributes

        self.key_check_value = _key_check_value()
        self.key_check_value_algorithm = key_check_value_algorithm

        self.exportable = exportable
        self.enabled = enabled
        self.key_state = "CREATE_COMPLETE"

        # when a key is created, the origin is AWS_PAYMENT_CRYPTOGRAPHY.
        # If a key is imported, the origin is EXTERNAL.
        self.key_origin = "AWS_PAYMENT_CRYPTOGRAPHY"
        self.create_time = datetime.now(timezone.utc)
        self.usage_start_timestamp = self.create_time if enabled else None
        self.usage_stop_timestamp = None
        self.delete_pending_timestamp = None
        self.delete_timestamp = None
        self.derive_key_usage = derive_key_usage

        if replication_regions is not None:
            self.multi_region_key_type = "PRIMARY"
            self.primary_region = region_name
            self.replication_status = dict()
            for region in replication_regions:
                self.replication_status[region] = {
                    "replication_status": "SYNCHRONIZED",
                    "status_message": "Key is synchronized across regions.",
                }
            self.using_default_replication_regions = False


        self.tags = tags
        self.derive_key_usage = derive_key_usage
        self.replication_regions = replication_regions


class PaymentCryptographyControlPlaneBackend(BaseBackend):
    """Implementation of PaymentCryptographyControlPlane APIs."""

    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)


paymentcryptography_backends = BackendDict(PaymentCryptographyControlPlaneBackend, "payment-cryptography")
