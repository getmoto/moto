from __future__ import unicode_literals
from .responses import ElasticTranscoderResponse

url_bases = [
    r"https?://elastictranscoder\.(.+)\.amazonaws.com",
]


response = ElasticTranscoderResponse()


url_paths = {
    r"{0}/(?P<api_version>[^/]+)/pipelines/?$": response.pipelines,
    r"{0}/(?P<api_version>[^/]+)/pipelines/(?P<pipeline_id>[^/]+)/?$": response.individual_pipeline,
}
