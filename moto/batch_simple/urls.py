from ..batch.urls import url_bases as batch_url_bases
from ..batch.urls import url_paths as batch_url_paths
from .responses import BatchSimpleResponse

url_bases = batch_url_bases.copy()
url_paths = {k: BatchSimpleResponse.dispatch for k in batch_url_paths}
