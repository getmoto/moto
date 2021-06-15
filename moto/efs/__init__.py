from __future__ import unicode_literals
from .models import efs_backends
from ..core.models import base_decorator

efs_backend = efs_backends["us-east-1"]
mock_efs = base_decorator(efs_backends)
