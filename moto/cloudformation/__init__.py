from __future__ import unicode_literals
from .models import cloudformation_backends
from ..core.models import base_decorator, deprecated_base_decorator

cloudformation_backend = cloudformation_backends["us-east-1"]
mock_cloudformation = base_decorator(cloudformation_backends)
mock_cloudformation_deprecated = deprecated_base_decorator(cloudformation_backends)
