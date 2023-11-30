"""Firehose module initialization; sets value for base decorator."""
from ..core.models import base_decorator
from .models import firehose_backends

mock_firehose = base_decorator(firehose_backends)
