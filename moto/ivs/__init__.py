"""ivs module initialization; sets value for base decorator."""
from ..core.models import base_decorator
from .models import ivs_backends

mock_ivs = base_decorator(ivs_backends)
