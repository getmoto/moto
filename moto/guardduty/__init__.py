from ..core.models import base_decorator
from .models import guardduty_backends

guardduty_backend = guardduty_backends["us-east-1"]
mock_guardduty = base_decorator(guardduty_backends)
