from .models import mediapackage_backends
from ..core.models import base_decorator

mediapackage_backend = mediapackage_backends["us-east-1"]
mock_mediapackage = base_decorator(mediapackage_backends)
