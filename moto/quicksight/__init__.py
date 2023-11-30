"""quicksight module initialization; sets value for base decorator."""
from ..core.models import base_decorator
from .models import quicksight_backends

mock_quicksight = base_decorator(quicksight_backends)
