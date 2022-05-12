from .models import kinesisvideo_backends
from ..core.models import base_decorator

kinesisvideo_backend = kinesisvideo_backends["us-east-1"]
mock_kinesisvideo = base_decorator(kinesisvideo_backends)
