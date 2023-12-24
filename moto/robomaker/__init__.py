"""robomaker module initialization; sets value for base decorator."""
from ..core.models import base_decorator
from .models import robomaker_backends

mock_robomaker = base_decorator(robomaker_backends)
