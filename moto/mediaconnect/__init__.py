from .models import mediaconnect_backends
from ..core.models import base_decorator

mediaconnect_backend = mediaconnect_backends["us-east-1"]
mock_mediaconnect = base_decorator(mediaconnect_backends)
