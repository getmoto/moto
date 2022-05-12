"""es module initialization; sets value for base decorator."""
from .models import es_backends
from ..core.models import base_decorator

mock_es = base_decorator(es_backends)
