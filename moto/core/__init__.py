from __future__ import unicode_literals
from .models import BaseModel, BaseBackend, moto_api_backend  # flake8: noqa

moto_api_backends = {"global": moto_api_backend}
