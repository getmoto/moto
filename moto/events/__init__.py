from __future__ import unicode_literals

from .models import events_backend

events_backends = {"global": events_backend}
mock_events = events_backend.decorator
