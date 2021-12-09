"""Firehose module initialization; sets value for base decorator."""
from .models import firehose_backends
from ..core.models import base_decorator

mock_firehose = base_decorator(firehose_backends)
