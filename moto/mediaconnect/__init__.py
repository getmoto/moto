from ..core.models import base_decorator
from .models import mediaconnect_backends

mediaconnect_backend = mediaconnect_backends["us-east-1"]
mock_mediaconnect = base_decorator(mediaconnect_backends)
