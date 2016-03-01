from __future__ import unicode_literals
from .responses import APIGatewayResponse

url_bases = [
    "https?://apigateway.(.+).amazonaws.com"
]

url_paths = {
    '{0}/restapis': APIGatewayResponse().restapis,
    '{0}/restapis/(?P<function_id>[^/]+)/?$': APIGatewayResponse().restapis_individual,
}
