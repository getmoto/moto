from ..core.models import base_decorator
from .models import events_backends

events_backend = events_backends["us-east-1"]
mock_events = base_decorator(events_backends)
