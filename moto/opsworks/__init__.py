from ..core.models import base_decorator
from .models import opsworks_backends

opsworks_backend = opsworks_backends["us-east-1"]
mock_opsworks = base_decorator(opsworks_backends)
