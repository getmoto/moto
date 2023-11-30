from ..core.models import base_decorator
from .models import elastictranscoder_backends

mock_elastictranscoder = base_decorator(elastictranscoder_backends)
