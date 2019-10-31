from __future__ import unicode_literals

from .models import events_backends
from ..core.models import base_decorator

events_backend = events_backends["us-east-1"]
mock_events = base_decorator(events_backends)
