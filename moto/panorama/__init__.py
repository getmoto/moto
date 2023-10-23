from .models import panorama_backends
from ..core.models import base_decorator

mock_panorama = base_decorator(panorama_backends)
