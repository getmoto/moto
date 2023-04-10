"""scheduler module initialization; sets value for base decorator."""
from .models import scheduler_backends
from ..core.models import base_decorator

mock_scheduler = base_decorator(scheduler_backends)
