from ..core.models import base_decorator
from .models import mediastore_backends

mediastore_backend = mediastore_backends["us-east-1"]
mock_mediastore = base_decorator(mediastore_backends)
