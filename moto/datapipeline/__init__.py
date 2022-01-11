from .models import datapipeline_backends
from ..core.models import base_decorator, deprecated_base_decorator

mock_datapipeline = base_decorator(datapipeline_backends)
mock_datapipeline_deprecated = deprecated_base_decorator(datapipeline_backends)
