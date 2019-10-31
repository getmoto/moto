from __future__ import unicode_literals
from .models import datapipeline_backends
from ..core.models import base_decorator, deprecated_base_decorator

datapipeline_backend = datapipeline_backends["us-east-1"]
mock_datapipeline = base_decorator(datapipeline_backends)
mock_datapipeline_deprecated = deprecated_base_decorator(datapipeline_backends)
