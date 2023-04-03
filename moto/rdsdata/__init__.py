"""rdsdata module initialization; sets value for base decorator."""
from .models import rdsdata_backends
from ..core.models import base_decorator

mock_rdsdata = base_decorator(rdsdata_backends)
