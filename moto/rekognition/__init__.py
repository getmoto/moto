"""rekognition module initialization; sets value for base decorator."""
from ..core.models import base_decorator
from .models import rekognition_backends

mock_rekognition = base_decorator(rekognition_backends)
