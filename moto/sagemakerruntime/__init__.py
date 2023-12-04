"""sagemakerruntime module initialization; sets value for base decorator."""
from ..core.models import base_decorator
from .models import sagemakerruntime_backends

mock_sagemakerruntime = base_decorator(sagemakerruntime_backends)
