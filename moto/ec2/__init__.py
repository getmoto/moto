from .models import ec2_backends
from ..core.models import base_decorator

mock_ec2 = base_decorator(ec2_backends)
