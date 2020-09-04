from __future__ import unicode_literals
from .models import kinesisvideoarchivedmedia_backends
from ..core.models import base_decorator

kinesisvideoarchivedmedia_backend = kinesisvideoarchivedmedia_backends["us-east-1"]
mock_kinesisvideoarchivedmedia = base_decorator(kinesisvideoarchivedmedia_backends)
