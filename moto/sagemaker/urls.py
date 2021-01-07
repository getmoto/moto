from __future__ import unicode_literals
from .responses import SageMakerResponse

url_bases = [
    "https?://api.sagemaker.(.+).amazonaws.com",
]

url_paths = {
    "{0}/$": SageMakerResponse.dispatch,
}
