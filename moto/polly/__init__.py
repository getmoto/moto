from ..core.models import base_decorator
from .models import polly_backends

polly_backend = polly_backends["us-east-1"]
mock_polly = base_decorator(polly_backends)
