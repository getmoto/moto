from .models import secretsmanager_backends
from ..core.models import base_decorator

secretsmanager_backend = secretsmanager_backends["us-east-1"]
mock_secretsmanager = base_decorator(secretsmanager_backends)
