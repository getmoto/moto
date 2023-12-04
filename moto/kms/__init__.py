from ..core.models import base_decorator
from .models import kms_backends

kms_backend = kms_backends["us-east-1"]
mock_kms = base_decorator(kms_backends)
