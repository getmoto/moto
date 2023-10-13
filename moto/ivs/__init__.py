"""ivs module initialization; sets value for base decorator."""
from .models import ivs_backends
from ..core.models import base_decorator

mock_ivs = base_decorator(ivs_backends)
