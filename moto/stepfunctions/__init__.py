from __future__ import unicode_literals
from .models import stepfunction_backends
from ..core.models import base_decorator

stepfunction_backend = stepfunction_backends["us-east-1"]
mock_stepfunctions = base_decorator(stepfunction_backends)
