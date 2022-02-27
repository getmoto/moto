from .models import polly_backends
from ..core.models import base_decorator

polly_backend = polly_backends["us-east-1"]
mock_polly = base_decorator(polly_backends)
