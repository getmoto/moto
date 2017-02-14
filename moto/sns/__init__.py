from __future__ import unicode_literals
from .models import sns_backends
from ..core.models import MockAWS, base_decorator

sns_backend = sns_backends['us-east-1']
mock_sns = base_decorator(sns_backends)
