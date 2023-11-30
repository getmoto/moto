from ..core.models import base_decorator
from .models import datapipeline_backends

mock_datapipeline = base_decorator(datapipeline_backends)
