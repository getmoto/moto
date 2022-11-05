from .models import codepipeline_backends
from ..core.models import base_decorator

mock_codepipeline = base_decorator(codepipeline_backends)
