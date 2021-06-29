from __future__ import unicode_literals
from .models import mediastoredata_backends
from ..core.models import base_decorator

mediastoredata_backend = mediastoredata_backends["us-east-1"]
mock_mediastoredata = base_decorator(mediastoredata_backends)
