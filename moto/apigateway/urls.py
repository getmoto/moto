from __future__ import unicode_literals
from .responses import APIGatewayResponse

url_bases = [
    "https?://apigateway.(.+).amazonaws.com"
]

url_paths = {
    '{0}/restapis$': APIGatewayResponse().restapis,
    '{0}/restapis/(?P<function_id>[^/]+)/?$': APIGatewayResponse().restapis_individual,
    '{0}/restapis/(?P<function_id>[^/]+)/resources$': APIGatewayResponse().resources,
    '{0}/restapis/(?P<function_id>[^/]+)/stages$': APIGatewayResponse().restapis_stages,
    '{0}/restapis/(?P<function_id>[^/]+)/stages/(?P<stage_name>[^/]+)/?$': APIGatewayResponse().stages,
    '{0}/restapis/(?P<function_id>[^/]+)/deployments$': APIGatewayResponse().deployments,
    '{0}/restapis/(?P<function_id>[^/]+)/deployments/(?P<deployment_id>[^/]+)/?$': APIGatewayResponse().individual_deployment,
    '{0}/restapis/(?P<function_id>[^/]+)/resources/(?P<resource_id>[^/]+)/?$': APIGatewayResponse().resource_individual,
    '{0}/restapis/(?P<function_id>[^/]+)/resources/(?P<resource_id>[^/]+)/methods/(?P<method_name>[^/]+)/?$': APIGatewayResponse().resource_methods,
    '{0}/restapis/(?P<function_id>[^/]+)/resources/(?P<resource_id>[^/]+)/methods/(?P<method_name>[^/]+)/responses/(?P<status_code>\d+)$': APIGatewayResponse().resource_method_responses,
    '{0}/restapis/(?P<function_id>[^/]+)/resources/(?P<resource_id>[^/]+)/methods/(?P<method_name>[^/]+)/integration/?$': APIGatewayResponse().integrations,
    '{0}/restapis/(?P<function_id>[^/]+)/resources/(?P<resource_id>[^/]+)/methods/(?P<method_name>[^/]+)/integration/responses/(?P<status_code>\d+)/?$': APIGatewayResponse().integration_responses,
    '{0}/apikeys$': APIGatewayResponse().apikeys,
    '{0}/apikeys/(?P<apikey>[^/]+)': APIGatewayResponse().apikey_individual,
}
