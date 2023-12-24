from ..core.models import base_decorator
from .models import ec2_backends

mock_ec2 = base_decorator(ec2_backends)
