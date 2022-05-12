from .models import swf_backends
from ..core.models import base_decorator

mock_swf = base_decorator(swf_backends)
