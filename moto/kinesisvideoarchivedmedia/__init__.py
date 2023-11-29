from ..core.models import base_decorator
from .models import kinesisvideoarchivedmedia_backends

kinesisvideoarchivedmedia_backend = kinesisvideoarchivedmedia_backends["us-east-1"]
mock_kinesisvideoarchivedmedia = base_decorator(kinesisvideoarchivedmedia_backends)
