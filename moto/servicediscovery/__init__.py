"""servicediscovery module initialization; sets value for base decorator."""
from .models import servicediscovery_backends
from ..core.models import base_decorator

mock_servicediscovery = base_decorator(servicediscovery_backends)
