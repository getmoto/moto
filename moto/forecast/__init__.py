from ..core.models import base_decorator
from .models import forecast_backends

forecast_backend = forecast_backends["us-east-1"]
mock_forecast = base_decorator(forecast_backends)
