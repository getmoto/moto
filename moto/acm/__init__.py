from ..core.models import base_decorator
from .models import acm_backends

acm_backend = acm_backends["us-east-1"]
mock_acm = base_decorator(acm_backends)
