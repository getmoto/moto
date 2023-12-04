from ..core.models import base_decorator
from .models import kinesisvideo_backends

kinesisvideo_backend = kinesisvideo_backends["us-east-1"]
mock_kinesisvideo = base_decorator(kinesisvideo_backends)
