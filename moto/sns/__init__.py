from .models import sns_backends
from ..core.models import base_decorator

mock_sns = base_decorator(sns_backends)
