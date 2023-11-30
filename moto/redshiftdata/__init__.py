from ..core.models import base_decorator
from .models import redshiftdata_backends

mock_redshiftdata = base_decorator(redshiftdata_backends)
