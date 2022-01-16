from .models import rds2_backends
from ..core.models import base_decorator, deprecated_base_decorator

rds2_backend = rds2_backends["us-west-1"]
mock_rds2 = base_decorator(rds2_backends)
mock_rds2_deprecated = deprecated_base_decorator(rds2_backends)
