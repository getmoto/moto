from .models import elastictranscoder_backends
from ..core.models import base_decorator

mock_elastictranscoder = base_decorator(elastictranscoder_backends)
