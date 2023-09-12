"""robomaker module initialization; sets value for base decorator."""
from .models import robomaker_backends
from ..core.models import base_decorator

mock_robomaker = base_decorator(robomaker_backends)
