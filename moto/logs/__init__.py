from .models import logs_backends
from ..core.models import base_decorator

mock_logs = base_decorator(logs_backends)
