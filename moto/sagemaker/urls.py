from .responses import SageMakerResponse
from moto.s3.responses import S3ResponseInstance

url_bases = [
    r"https?://api\.sagemaker\.(.+)\.amazonaws.com",
    # r"https?://(?P<bucket_name>[a-zA-Z0-9\-_.]*)\.?s3(?!-control)(.*)\.amazonaws.com",
]

url_paths = {
    "{0}/$": SageMakerResponse.dispatch,
    # "{0}/$": S3ResponseInstance.bucket_response,
}
