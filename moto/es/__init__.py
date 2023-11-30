"""es module initialization; sets value for base decorator."""
from ..core.models import base_decorator
from .models import es_backends

mock_es = base_decorator(es_backends)
