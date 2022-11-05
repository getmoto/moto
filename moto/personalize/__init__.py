"""personalize module initialization; sets value for base decorator."""
from .models import personalize_backends
from ..core.models import base_decorator

mock_personalize = base_decorator(personalize_backends)
