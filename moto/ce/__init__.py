"""ce module initialization; sets value for base decorator."""
from ..core.models import base_decorator
from .models import ce_backends

mock_ce = base_decorator(ce_backends)
