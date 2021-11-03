from .models import medialive_backends
from ..core.models import base_decorator

medialive_backend = medialive_backends["us-east-1"]
mock_medialive = base_decorator(medialive_backends)
