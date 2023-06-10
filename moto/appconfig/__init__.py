"""appconfig module initialization; sets value for base decorator."""
from .models import appconfig_backends
from ..core.models import base_decorator

mock_appconfig = base_decorator(appconfig_backends)
