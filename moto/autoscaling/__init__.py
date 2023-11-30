from ..core.models import base_decorator
from .models import autoscaling_backends

autoscaling_backend = autoscaling_backends["us-east-1"]
mock_autoscaling = base_decorator(autoscaling_backends)
