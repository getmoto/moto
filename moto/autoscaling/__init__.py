from __future__ import unicode_literals
from .models import autoscaling_backends
from ..core.models import base_decorator, deprecated_base_decorator

autoscaling_backend = autoscaling_backends["us-east-1"]
mock_autoscaling = base_decorator(autoscaling_backends)
mock_autoscaling_deprecated = deprecated_base_decorator(autoscaling_backends)
