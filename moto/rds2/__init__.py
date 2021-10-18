from .models import rds2_backends
from ..core.models import base_decorator

rds2_backend = rds2_backends["us-west-1"]
mock_rds2 = base_decorator(rds2_backends)
