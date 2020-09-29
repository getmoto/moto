from __future__ import unicode_literals

from .models import transcribe_backends

transcribe_backend = transcribe_backends["us-east-1"]
mock_transcribe = transcribe_backend.decorator
