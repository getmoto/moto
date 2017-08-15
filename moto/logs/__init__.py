from .models import logs_backends
from ..core.models import base_decorator, deprecated_base_decorator

mock_logs = base_decorator(logs_backends)
mock_logs_deprecated = deprecated_base_decorator(logs_backends)
