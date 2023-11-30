"""opensearch module initialization; sets value for base decorator."""
from ..core.models import base_decorator
from .models import opensearch_backends

mock_opensearch = base_decorator(opensearch_backends)
