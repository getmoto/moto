from .models import medialive_backends
from ..core.models import base_decorator

mock_medialive = base_decorator(medialive_backends)
