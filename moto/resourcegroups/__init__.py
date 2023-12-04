from ..core.models import base_decorator
from .models import resourcegroups_backends

resourcegroups_backend = resourcegroups_backends["us-east-1"]
mock_resourcegroups = base_decorator(resourcegroups_backends)
