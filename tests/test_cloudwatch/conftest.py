import pytest
from botocore.model import ServiceModel

from moto.core.utils import get_service_model

CLOUDWATCH_PROTOCOLS = get_service_model("cloudwatch").metadata["protocols"]


@pytest.fixture(autouse=True, params=CLOUDWATCH_PROTOCOLS)
def cloudwatch_protocol(request, monkeypatch):
    """Run every CloudWatch test against each protocol the service supports.
    Botocore picks the first protocol from its own priority list that the service
    supports, so we override the resolved protocol for CloudWatch clients only.
    """
    protocol = request.param
    original = ServiceModel.__dict__["resolved_protocol"]

    def resolved_protocol(self):
        if self.service_name == "cloudwatch":
            return protocol
        return original.__get__(self, type(self))

    monkeypatch.setattr(ServiceModel, "resolved_protocol", property(resolved_protocol))
    return protocol
