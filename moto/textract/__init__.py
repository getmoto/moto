"""textract module initialization; sets value for base decorator."""
from .models import textract_backends
from ..core.models import base_decorator

mock_textract = base_decorator(textract_backends)
