from __future__ import unicode_literals
from .models import emr_backends
from ..core.models import base_decorator, deprecated_base_decorator

emr_backend = emr_backends["us-east-1"]
mock_emr = base_decorator(emr_backends)
mock_emr_deprecated = deprecated_base_decorator(emr_backends)
