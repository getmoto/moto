from .models import kms_backends
from ..core.models import base_decorator

kms_backend = kms_backends["us-east-1"]
mock_kms = base_decorator(kms_backends)
