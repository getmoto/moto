"""amp module initialization; sets value for base decorator."""
from .models import amp_backends
from ..core.models import base_decorator

mock_amp = base_decorator(amp_backends)
