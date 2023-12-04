from ..core.models import base_decorator
from .models import emr_backends

emr_backend = emr_backends["us-east-1"]
mock_emr = base_decorator(emr_backends)
