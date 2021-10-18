from .models import swf_backends
from ..core.models import base_decorator

swf_backend = swf_backends["us-east-1"]
mock_swf = base_decorator(swf_backends)
