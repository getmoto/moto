from ..core.models import base_decorator
from .models import medialive_backends

mock_medialive = base_decorator(medialive_backends)
