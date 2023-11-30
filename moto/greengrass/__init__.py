from ..core.models import base_decorator
from .models import greengrass_backends

mock_greengrass = base_decorator(greengrass_backends)
