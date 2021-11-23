from .models import ec2_backends
from ..core.models import base_decorator, deprecated_base_decorator

ec2_backend = ec2_backends["us-east-1"]
mock_ec2 = base_decorator(ec2_backends)
mock_ec2_deprecated = deprecated_base_decorator(ec2_backends)
