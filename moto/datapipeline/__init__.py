from __future__ import unicode_literals
from .models import datapipeline_backends
from ..core.models import MockAWS

datapipeline_backend = datapipeline_backends['us-east-1']


def mock_datapipeline(func=None):
    if func:
        return MockAWS(datapipeline_backends)(func)
    else:
        return MockAWS(datapipeline_backends)
