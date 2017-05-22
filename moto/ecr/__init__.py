from __future__ import unicode_literals
from .models import ecr_backends
from ..core.models import base_decorator, deprecated_base_decorator

ecr_backend = ecr_backends['us-east-1']
mock_ecr = base_decorator(ecr_backends)
mock_ecr_deprecated = deprecated_base_decorator(ecr_backends)
