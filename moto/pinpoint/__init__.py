"""pinpoint module initialization; sets value for base decorator."""
from .models import pinpoint_backends
from ..core.models import base_decorator

mock_pinpoint = base_decorator(pinpoint_backends)
