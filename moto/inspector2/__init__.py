"""inspector2 module initialization; sets value for base decorator."""
from ..core.models import base_decorator
from .models import inspector2_backends

mock_inspector2 = base_decorator(inspector2_backends)
