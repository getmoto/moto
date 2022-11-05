"""quicksight module initialization; sets value for base decorator."""
from .models import quicksight_backends
from ..core.models import base_decorator

mock_quicksight = base_decorator(quicksight_backends)
