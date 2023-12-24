from ..core.models import base_decorator
from .models import elb_backends

elb_backend = elb_backends["us-east-1"]
mock_elb = base_decorator(elb_backends)
