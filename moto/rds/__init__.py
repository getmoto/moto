from .models import rds_backends
from ..core.models import base_decorator

mock_rds = base_decorator(rds_backends)
