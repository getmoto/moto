from __future__ import unicode_literals

from .models import wafv2_backends, GLOBAL_REGION
from ..core.models import base_decorator

wafv2_backend = wafv2_backends[GLOBAL_REGION]
mock_wafv2 = base_decorator(wafv2_backends)
