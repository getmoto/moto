from ..core.models import base_decorator
from .models import mediastoredata_backends

mediastoredata_backend = mediastoredata_backends["us-east-1"]
mock_mediastoredata = base_decorator(mediastoredata_backends)
