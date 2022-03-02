import os
from .models import sns_backends
from ..core.models import base_decorator

region_name = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
sns_backend = sns_backends[region_name]
mock_sns = base_decorator(sns_backends)
