"""emrcontainers module initialization; sets value for base decorator."""
from ..core.models import base_decorator
from .models import emrcontainers_backends

REGION = "us-east-1"
mock_emrcontainers = base_decorator(emrcontainers_backends)
