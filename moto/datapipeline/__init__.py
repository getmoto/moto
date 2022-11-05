from .models import datapipeline_backends
from ..core.models import base_decorator

mock_datapipeline = base_decorator(datapipeline_backends)
