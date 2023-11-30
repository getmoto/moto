"""scheduler module initialization; sets value for base decorator."""
from ..core.models import base_decorator
from .models import scheduler_backends

mock_scheduler = base_decorator(scheduler_backends)
