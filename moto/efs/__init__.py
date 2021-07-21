from __future__ import unicode_literals

from ..core.models import base_decorator
from .models import efs_backends

efs_backend = efs_backends["us-east-1"]
mock_efs = base_decorator(efs_backends)
