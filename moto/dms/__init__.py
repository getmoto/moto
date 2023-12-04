from ..core.models import base_decorator
from .models import dms_backends

dms_backend = dms_backends["us-east-1"]
mock_dms = base_decorator(dms_backends)
