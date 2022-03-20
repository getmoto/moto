"""rekognition module initialization; sets value for base decorator."""
from .models import rekognition_backends
from ..core.models import base_decorator

mock_rekognition = base_decorator(rekognition_backends)
