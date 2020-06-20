from __future__ import unicode_literals
from .models import applicationautoscaling_backends
from ..core.models import base_decorator

applicationautoscaling_backend = applicationautoscaling_backends["us-east-1"]
mock_applicationautoscaling = base_decorator(applicationautoscaling_backends)
# mock_applicationautoscaling_deprecated = deprecated_base_decorator(
#     applicationautoscaling_backends
# )
