"""servicequotas module initialization; sets value for base decorator."""
from ..core.models import base_decorator
from .models import servicequotas_backends

mock_servicequotas = base_decorator(servicequotas_backends)
