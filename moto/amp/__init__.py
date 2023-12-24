"""amp module initialization; sets value for base decorator."""
from ..core.models import base_decorator
from .models import amp_backends

mock_amp = base_decorator(amp_backends)
