from __future__ import unicode_literals
from .models import kms_backends
from ..core.models import base_decorator, deprecated_base_decorator

kms_backend = kms_backends["us-east-1"]
mock_kms = base_decorator(kms_backends)
mock_kms_deprecated = deprecated_base_decorator(kms_backends)
