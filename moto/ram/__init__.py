from .models import ram_backends
from ..core.models import base_decorator

ram_backend = ram_backends["us-east-1"]
mock_ram = base_decorator(ram_backends)
