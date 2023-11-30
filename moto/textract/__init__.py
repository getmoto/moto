"""textract module initialization; sets value for base decorator."""
from ..core.models import base_decorator
from .models import textract_backends

mock_textract = base_decorator(textract_backends)
