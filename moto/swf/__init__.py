from ..core.models import base_decorator
from .models import swf_backends

mock_swf = base_decorator(swf_backends)
