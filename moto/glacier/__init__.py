from __future__ import unicode_literals
from .models import glacier_backends
from ..core.models import base_decorator, deprecated_base_decorator

glacier_backend = glacier_backends["us-east-1"]
mock_glacier = base_decorator(glacier_backends)
mock_glacier_deprecated = deprecated_base_decorator(glacier_backends)
