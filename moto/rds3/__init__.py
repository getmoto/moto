from __future__ import unicode_literals

from .models import rds3_backends
from ..core.models import base_decorator, deprecated_base_decorator

rds3_backend = rds3_backends["us-west-1"]
mock_rds3 = base_decorator(rds3_backends)
mock_rds3_deprecated = deprecated_base_decorator(rds3_backends)
