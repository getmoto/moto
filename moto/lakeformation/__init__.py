"""lakeformation module initialization; sets value for base decorator."""
from .models import lakeformation_backends
from ..core.models import base_decorator

mock_lakeformation = base_decorator(lakeformation_backends)
