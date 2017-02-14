from __future__ import unicode_literals
from .models import datapipeline_backends
from ..core.models import MockAWS, base_decorator

datapipeline_backend = datapipeline_backends['us-east-1']
mock_datapipeline = base_decorator(datapipeline_backends)
