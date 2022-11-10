from .models import greengrass_backends
from ..core.models import base_decorator

mock_greengrass = base_decorator(greengrass_backends)
