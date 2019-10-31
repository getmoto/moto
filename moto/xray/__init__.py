from __future__ import unicode_literals
from .models import xray_backends
from ..core.models import base_decorator
from .mock_client import mock_xray_client, XRaySegment  # noqa

xray_backend = xray_backends["us-east-1"]
mock_xray = base_decorator(xray_backends)
