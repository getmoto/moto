from ..core.models import base_decorator
from .models import timestreamwrite_backends

mock_timestreamwrite = base_decorator(timestreamwrite_backends)
