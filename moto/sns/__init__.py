from ..core.models import base_decorator
from .models import sns_backends

mock_sns = base_decorator(sns_backends)
