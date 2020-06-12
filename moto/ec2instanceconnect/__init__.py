from ..core.models import base_decorator
from .models import ec2instanceconnect_backends

mock_ec2instanceconnect = base_decorator(ec2instanceconnect_backends)
