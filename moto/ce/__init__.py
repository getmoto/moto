"""ce module initialization; sets value for base decorator."""
from .models import ce_backends
from ..core.models import base_decorator

mock_ce = base_decorator(ce_backends)
