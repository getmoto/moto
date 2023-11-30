from ..core.models import base_decorator
from .models import transcribe_backends

transcribe_backend = transcribe_backends["us-east-1"]
mock_transcribe = base_decorator(transcribe_backends)
