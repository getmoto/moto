from .models import rds_backends
from ..core.models import base_decorator, deprecated_base_decorator

mock_rds = base_decorator(rds_backends)
mock_rds_deprecated = deprecated_base_decorator(rds_backends)
