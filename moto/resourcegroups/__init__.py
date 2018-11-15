from __future__ import unicode_literals
from .models import resourcegroups_backends
from ..core.models import base_decorator

resourcegroups_backend = resourcegroups_backends['us-east-1']
mock_resourcegroups = base_decorator(resourcegroups_backends)
