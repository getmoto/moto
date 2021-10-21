"""emrcontainers module initialization; sets value for base decorator."""
from .models import emrcontainers_backends
from ..core.models import base_decorator, deprecated_base_decorator

emrcontainers_backends = emrcontainers_backends["us-east-1"]
mock_emrcontainers = base_decorator(emrcontainers_backends)
mock_emrcontainers_deprecated = deprecated_base_decorator(emrcontainers_backends)