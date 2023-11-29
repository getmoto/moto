"""lakeformation module initialization; sets value for base decorator."""
from ..core.models import base_decorator
from .models import lakeformation_backends

mock_lakeformation = base_decorator(lakeformation_backends)
