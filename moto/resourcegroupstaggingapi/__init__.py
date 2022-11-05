from .models import resourcegroupstaggingapi_backends
from ..core.models import base_decorator

resourcegroupstaggingapi_backend = resourcegroupstaggingapi_backends["us-east-1"]
mock_resourcegroupstaggingapi = base_decorator(resourcegroupstaggingapi_backends)
