"""pinpoint module initialization; sets value for base decorator."""
from ..core.models import base_decorator
from .models import pinpoint_backends

mock_pinpoint = base_decorator(pinpoint_backends)
