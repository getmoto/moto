"""appsync module initialization; sets value for base decorator."""
from ..core.models import base_decorator
from .models import appsync_backends

mock_appsync = base_decorator(appsync_backends)
