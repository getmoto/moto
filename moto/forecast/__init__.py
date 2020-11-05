from __future__ import unicode_literals

from .models import forecast_backends
from ..core.models import base_decorator

forecast_backend = forecast_backends["us-east-1"]
mock_forecast = base_decorator(forecast_backends)
