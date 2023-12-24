from ..core.models import base_decorator
from .models import logs_backends

mock_logs = base_decorator(logs_backends)
