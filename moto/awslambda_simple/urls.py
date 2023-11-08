from ..awslambda.urls import url_bases as lambda_url_bases
from ..awslambda.urls import url_paths as lambda_url_paths
from .responses import LambdaSimpleResponse

url_bases = lambda_url_bases.copy()
url_paths = {
    k: LambdaSimpleResponse.method_dispatch(v) for k, v in lambda_url_paths.items()  # type: ignore
}
