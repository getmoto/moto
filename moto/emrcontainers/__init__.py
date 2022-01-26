"""emrcontainers module initialization; sets value for base decorator."""
from .models import emrcontainers_backends
from ..core.models import base_decorator

REGION = "us-east-1"
mock_emrcontainers = base_decorator(emrcontainers_backends)
