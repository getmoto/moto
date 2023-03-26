"""opensearch module initialization; sets value for base decorator."""
from .models import opensearch_backends
from ..core.models import base_decorator

mock_opensearch = base_decorator(opensearch_backends)
