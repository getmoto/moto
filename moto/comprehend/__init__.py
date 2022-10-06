"""comprehend module initialization; sets value for base decorator."""
from .models import comprehend_backends
from ..core.models import base_decorator

mock_comprehend = base_decorator(comprehend_backends)
