from .models import sns_backends
from ..core.models import base_decorator, deprecated_base_decorator

sns_backend = sns_backends["us-east-1"]
mock_sns = base_decorator(sns_backends)
mock_sns_deprecated = deprecated_base_decorator(sns_backends)
