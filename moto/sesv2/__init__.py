"""sesv2 module initialization; sets value for base decorator."""
from ..core.models import base_decorator
from .models import sesv2_backends

mock_sesv2 = base_decorator(sesv2_backends)
