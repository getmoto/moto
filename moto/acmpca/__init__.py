"""acmpca module initialization; sets value for base decorator."""
from ..core.models import base_decorator
from .models import acmpca_backends

mock_acmpca = base_decorator(acmpca_backends)
