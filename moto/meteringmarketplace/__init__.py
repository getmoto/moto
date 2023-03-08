from .models import meteringmarketplace_backends
from ..core.models import base_decorator

meteringmarketplace_backend = meteringmarketplace_backends["us-east-1"]
mock_meteringmarketplace = base_decorator(meteringmarketplace_backends)
