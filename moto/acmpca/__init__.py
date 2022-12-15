"""acmpca module initialization; sets value for base decorator."""
from .models import acmpca_backends
from ..core.models import base_decorator

mock_acmpca = base_decorator(acmpca_backends)
