from ..core.models import base_decorator
from .models import panorama_backends

mock_panorama = base_decorator(panorama_backends)
