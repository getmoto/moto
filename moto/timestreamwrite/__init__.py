from .models import timestreamwrite_backends
from ..core.models import base_decorator

mock_timestreamwrite = base_decorator(timestreamwrite_backends)
