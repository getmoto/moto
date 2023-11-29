"""servicediscovery module initialization; sets value for base decorator."""
from ..core.models import base_decorator
from .models import servicediscovery_backends

mock_servicediscovery = base_decorator(servicediscovery_backends)
