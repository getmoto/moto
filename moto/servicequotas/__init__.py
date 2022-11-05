"""servicequotas module initialization; sets value for base decorator."""
from .models import servicequotas_backends
from ..core.models import base_decorator

mock_servicequotas = base_decorator(servicequotas_backends)
