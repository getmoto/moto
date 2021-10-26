from .models import elastictranscoder_backends
from ..core.models import base_decorator

elastictranscoder_backend = elastictranscoder_backends["us-east-1"]
mock_elastictranscoder = base_decorator(elastictranscoder_backends)
