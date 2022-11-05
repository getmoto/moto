from .models import transcribe_backends
from ..core.models import base_decorator

transcribe_backend = transcribe_backends["us-east-1"]
mock_transcribe = base_decorator(transcribe_backends)
