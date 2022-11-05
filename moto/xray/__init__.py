from .models import xray_backends
from ..core.models import base_decorator
from .mock_client import MockXrayClient, XRaySegment  # noqa

xray_backend = xray_backends["us-east-1"]
mock_xray = base_decorator(xray_backends)
mock_xray_client = MockXrayClient()
