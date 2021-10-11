from __future__ import unicode_literals
from .responses import APIGatewayResponse

response = APIGatewayResponse()

url_bases = [r"https?://apigateway\.(.+)\.amazonaws.com"]

url_paths = {
    "{0}/restapis$": response.restapis,
    "{0}/restapis/(?P<function_id>[^/]+)/?$": response.restapis_individual,
    "{0}/restapis/(?P<function_id>[^/]+)/resources$": response.resources,
    "{0}/restapis/(?P<function_id>[^/]+)/authorizers$": response.restapis_authorizers,
    "{0}/restapis/(?P<function_id>[^/]+)/authorizers/(?P<authorizer_id>[^/]+)/?$": response.authorizers,
    "{0}/restapis/(?P<function_id>[^/]+)/stages$": response.restapis_stages,
    "{0}/tags/arn:aws:apigateway:(?P<region_name>[^/]+)::/restapis/(?P<function_id>[^/]+)/stages/(?P<stage_name>[^/]+)/?$": response.restapis_stages_tags,
    "{0}/restapis/(?P<function_id>[^/]+)/stages/(?P<stage_name>[^/]+)/?$": response.stages,
    "{0}/restapis/(?P<function_id>[^/]+)/deployments$": response.deployments,
    "{0}/restapis/(?P<function_id>[^/]+)/deployments/(?P<deployment_id>[^/]+)/?$": response.individual_deployment,
    "{0}/restapis/(?P<function_id>[^/]+)/resources/(?P<resource_id>[^/]+)/?$": response.resource_individual,
    "{0}/restapis/(?P<function_id>[^/]+)/resources/(?P<resource_id>[^/]+)/methods/(?P<method_name>[^/]+)/?$": response.resource_methods,
    r"{0}/restapis/(?P<function_id>[^/]+)/resources/(?P<resource_id>[^/]+)/methods/(?P<method_name>[^/]+)/responses/(?P<status_code>\d+)$": response.resource_method_responses,
    "{0}/restapis/(?P<function_id>[^/]+)/resources/(?P<resource_id>[^/]+)/methods/(?P<method_name>[^/]+)/integration/?$": response.integrations,
    r"{0}/restapis/(?P<function_id>[^/]+)/resources/(?P<resource_id>[^/]+)/methods/(?P<method_name>[^/]+)/integration/responses/(?P<status_code>\d+)/?$": response.integration_responses,
    "{0}/apikeys$": response.apikeys,
    "{0}/apikeys/(?P<apikey>[^/]+)": response.apikey_individual,
    "{0}/usageplans$": response.usage_plans,
    "{0}/domainnames$": response.domain_names,
    "{0}/restapis/(?P<function_id>[^/]+)/models$": response.models,
    "{0}/restapis/(?P<function_id>[^/]+)/models/(?P<model_name>[^/]+)/?$": response.model_induvidual,
    "{0}/domainnames/(?P<domain_name>[^/]+)/?$": response.domain_name_induvidual,
    "{0}/usageplans/(?P<usage_plan_id>[^/]+)/?$": response.usage_plan_individual,
    "{0}/usageplans/(?P<usage_plan_id>[^/]+)/keys$": response.usage_plan_keys,
    "{0}/usageplans/(?P<usage_plan_id>[^/]+)/keys/(?P<api_key_id>[^/]+)/?$": response.usage_plan_key_individual,
    "{0}/restapis/(?P<function_id>[^/]+)/requestvalidators$": response.request_validators,
    "{0}/restapis/(?P<api_id>[^/]+)/requestvalidators/(?P<validator_id>[^/]+)/?$": response.request_validator_individual,
}
