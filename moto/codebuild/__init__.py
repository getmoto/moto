from .models import codebuild_backends
from ..core.models import base_decorator

mock_codebuild = base_decorator(codebuild_backends)
