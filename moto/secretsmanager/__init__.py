from ..core.models import base_decorator
from .models import secretsmanager_backends

secretsmanager_backend = secretsmanager_backends["us-east-1"]
mock_secretsmanager = base_decorator(secretsmanager_backends)
