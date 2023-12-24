"""rdsdata module initialization; sets value for base decorator."""
from ..core.models import base_decorator
from .models import rdsdata_backends

mock_rdsdata = base_decorator(rdsdata_backends)
