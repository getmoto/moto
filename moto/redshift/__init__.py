from __future__ import unicode_literals
from .models import redshift_backends
from ..core.models import MockAWS, base_decorator

redshift_backend = redshift_backends['us-east-1']
mock_redshift = base_decorator(redshift_backends)
