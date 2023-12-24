from ..core.models import base_decorator
from .models import rds_backends

rds_backend = rds_backends["us-west-1"]
mock_rds = base_decorator(rds_backends)
