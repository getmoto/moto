from __future__ import unicode_literals
from .models import emr_backends
from ..core.models import MockAWS, base_decorator

emr_backend = emr_backends['us-east-1']
mock_emr = base_decorator(emr_backends)
