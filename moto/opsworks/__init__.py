from .models import opsworks_backends
from ..core.models import base_decorator

opsworks_backend = opsworks_backends["us-east-1"]
mock_opsworks = base_decorator(opsworks_backends)
