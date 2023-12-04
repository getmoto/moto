from ..core.models import base_decorator
from .models import meteringmarketplace_backends

meteringmarketplace_backend = meteringmarketplace_backends["us-east-1"]
mock_meteringmarketplace = base_decorator(meteringmarketplace_backends)
