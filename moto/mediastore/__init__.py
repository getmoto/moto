from __future__ import unicode_literals
from .models import mediastore_backends
from ..core.models import base_decorator

mediastore_backend = mediastore_backends["us-east-1"]
mock_mediastore = base_decorator(mediastore_backends)
