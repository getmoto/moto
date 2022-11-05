from .models import redshiftdata_backends
from ..core.models import base_decorator

mock_redshiftdata = base_decorator(redshiftdata_backends)
