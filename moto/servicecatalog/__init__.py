"""servicecatalog module initialization; sets value for base decorator."""
from .models import servicecatalog_backends
from ..core.models import base_decorator

mock_servicecatalog = base_decorator(servicecatalog_backends)