"""inspector2 module initialization; sets value for base decorator."""
from .models import inspector2_backends
from ..core.models import base_decorator

mock_inspector2 = base_decorator(inspector2_backends)
