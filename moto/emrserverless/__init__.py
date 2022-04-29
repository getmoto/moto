"""emrserverless module initialization; sets value for base decorator."""
from .models import emrserverless_backends
from ..core.models import base_decorator

mock_emrserverless = base_decorator(emrserverless_backends)
