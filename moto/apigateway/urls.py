from __future__ import unicode_literals
from .responses import APIGatewayResponse

url_bases = ["https?://apigateway.(.+).amazonaws.com"]

url_paths = {
    "{0}/restapis$": APIGatewayResponse().restapis,
    "{0}/restapis/(?P<function_id>[^/]+)/?$": APIGatewayResponse().restapis_individual,
    "{0}/restapis/(?P<function_id>[^/]+)/resources$": APIGatewayResponse().resources,
    "{0}/restapis/(?P<function_id>[^/]+)/authorizers$": APIGatewayResponse().restapis_authorizers,
    "{0}/restapis/(?P<function_id>[^/]+)/authorizers/(?P<authorizer_id>[^/]+)/?$": APIGatewayResponse().authorizers,
    "{0}/restapis/(?P<function_id>[^/]+)/stages$": APIGatewayResponse().restapis_stages,
    "{0}/restapis/(?P<function_id>[^/]+)/stages/(?P<stage_name>[^/]+)/?$": APIGatewayResponse().stages,
    "{0}/restapis/(?P<function_id>[^/]+)/deployments$": APIGatewayResponse().deployments,
    "{0}/restapis/(?P<function_id>[^/]+)/deployments/(?P<deployment_id>[^/]+)/?$": APIGatewayResponse().individual_deployment,
    "{0}/restapis/(?P<function_id>[^/]+)/resources/(?P<resource_id>[^/]+)/?$": APIGatewayResponse().resource_individual,
    "{0}/restapis/(?P<function_id>[^/]+)/resources/(?P<resource_id>[^/]+)/methods/(?P<method_name>[^/]+)/?$": APIGatewayResponse().resource_methods,
    r"{0}/restapis/(?P<function_id>[^/]+)/resources/(?P<resource_id>[^/]+)/methods/(?P<method_name>[^/]+)/responses/(?P<status_code>\d+)$": APIGatewayResponse().resource_method_responses,
    "{0}/restapis/(?P<function_id>[^/]+)/resources/(?P<resource_id>[^/]+)/methods/(?P<method_name>[^/]+)/integration/?$": APIGatewayResponse().integrations,
    r"{0}/restapis/(?P<function_id>[^/]+)/resources/(?P<resource_id>[^/]+)/methods/(?P<method_name>[^/]+)/integration/responses/(?P<status_code>\d+)/?$": APIGatewayResponse().integration_responses,
    "{0}/apikeys$": APIGatewayResponse().apikeys,
    "{0}/apikeys/(?P<apikey>[^/]+)": APIGatewayResponse().apikey_individual,
    "{0}/usageplans$": APIGatewayResponse().usage_plans,
    "{0}/domainnames$": APIGatewayResponse().domain_names,
    "{0}/restapis/(?P<function_id>[^/]+)/models$": APIGatewayResponse().models,
    "{0}/restapis/(?P<function_id>[^/]+)/models/(?P<model_name>[^/]+)/?$": APIGatewayResponse().model_induvidual,
    "{0}/domainnames/(?P<domain_name>[^/]+)/?$": APIGatewayResponse().domain_name_induvidual,
    "{0}/usageplans/(?P<usage_plan_id>[^/]+)/?$": APIGatewayResponse().usage_plan_individual,
    "{0}/usageplans/(?P<usage_plan_id>[^/]+)/keys$": APIGatewayResponse().usage_plan_keys,
    "{0}/usageplans/(?P<usage_plan_id>[^/]+)/keys/(?P<api_key_id>[^/]+)/?$": APIGatewayResponse().usage_plan_key_individual,
}
