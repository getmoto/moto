"""comprehend module initialization; sets value for base decorator."""
from ..core.models import base_decorator
from .models import comprehend_backends

mock_comprehend = base_decorator(comprehend_backends)
