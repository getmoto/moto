from .responses import APIGatewayResponse
from ..apigatewayv2.urls import url_paths as url_paths_v2

url_bases = [r"https?://apigateway\.(.+)\.amazonaws.com"]

url_paths = {
    "{0}/restapis$": APIGatewayResponse.method_dispatch(APIGatewayResponse.restapis),
    "{0}/restapis/(?P<function_id>[^/]+)/?$": APIGatewayResponse.method_dispatch(
        APIGatewayResponse.restapis_individual
    ),
    "{0}/restapis/(?P<function_id>[^/]+)/resources$": APIGatewayResponse.method_dispatch(
        APIGatewayResponse.resources
    ),
    "{0}/restapis/(?P<function_id>[^/]+)/authorizers$": APIGatewayResponse.method_dispatch(
        APIGatewayResponse.restapis_authorizers
    ),
    "{0}/restapis/(?P<function_id>[^/]+)/authorizers/(?P<authorizer_id>[^/]+)/?$": APIGatewayResponse.method_dispatch(
        APIGatewayResponse.authorizers
    ),
    "{0}/restapis/(?P<function_id>[^/]+)/stages$": APIGatewayResponse.method_dispatch(
        APIGatewayResponse.restapis_stages
    ),
    "{0}/tags/arn:aws:apigateway:(?P<region_name>[^/]+)::/restapis/(?P<function_id>[^/]+)/stages/(?P<stage_name>[^/]+)/?$": APIGatewayResponse.method_dispatch(
        APIGatewayResponse.restapis_stages_tags
    ),
    "{0}/restapis/(?P<function_id>[^/]+)/stages/(?P<stage_name>[^/]+)/?$": APIGatewayResponse.method_dispatch(
        APIGatewayResponse.stages
    ),
    "{0}/restapis/(?P<function_id>[^/]+)/stages/(?P<stage_name>[^/]+)/exports/(?P<export_type>[^/]+)/?$": APIGatewayResponse.method_dispatch(
        APIGatewayResponse.export
    ),
    "{0}/restapis/(?P<function_id>[^/]+)/deployments$": APIGatewayResponse.method_dispatch(
        APIGatewayResponse.deployments
    ),
    "{0}/restapis/(?P<function_id>[^/]+)/deployments/(?P<deployment_id>[^/]+)/?$": APIGatewayResponse.method_dispatch(
        APIGatewayResponse.individual_deployment
    ),
    "{0}/restapis/(?P<function_id>[^/]+)/resources/(?P<resource_id>[^/]+)/?$": APIGatewayResponse.method_dispatch(
        APIGatewayResponse.resource_individual
    ),
    "{0}/restapis/(?P<function_id>[^/]+)/resources/(?P<resource_id>[^/]+)/methods/(?P<method_name>[^/]+)/?$": APIGatewayResponse.method_dispatch(
        APIGatewayResponse.resource_methods
    ),
    r"{0}/restapis/(?P<function_id>[^/]+)/resources/(?P<resource_id>[^/]+)/methods/(?P<method_name>[^/]+)/responses/(?P<status_code>\d+)$": APIGatewayResponse.method_dispatch(
        APIGatewayResponse.resource_method_responses
    ),
    r"{0}/restapis/(?P<function_id>[^/]+)/resources/(?P<resource_id>[^/]+)/methods/(?P<method_name>[^/]+)/integration$": APIGatewayResponse.method_dispatch(
        APIGatewayResponse.integrations
    ),
    r"{0}/restapis/(?P<function_id>[^/]+)/resources/(?P<resource_id>[^/]+)/methods/(?P<method_name>[^/]+)/integration/responses/(?P<status_code>\d+)$": APIGatewayResponse.method_dispatch(
        APIGatewayResponse.integration_responses
    ),
    r"{0}/restapis/(?P<function_id>[^/]+)/resources/(?P<resource_id>[^/]+)/methods/(?P<method_name>[^/]+)/integration/responses/(?P<status_code>\d+)/$": APIGatewayResponse.method_dispatch(
        APIGatewayResponse.integration_responses
    ),
    "{0}/apikeys$": APIGatewayResponse.method_dispatch(APIGatewayResponse.apikeys),
    "{0}/apikeys/(?P<apikey>[^/]+)": APIGatewayResponse.method_dispatch(
        APIGatewayResponse.apikey_individual
    ),
    "{0}/usageplans$": APIGatewayResponse.method_dispatch(
        APIGatewayResponse.usage_plans
    ),
    "{0}/domainnames$": APIGatewayResponse.method_dispatch(
        APIGatewayResponse.domain_names
    ),
    "{0}/restapis/(?P<function_id>[^/]+)/models$": APIGatewayResponse.method_dispatch(
        APIGatewayResponse.models
    ),
    "{0}/restapis/(?P<function_id>[^/]+)/models/(?P<model_name>[^/]+)/?$": APIGatewayResponse.method_dispatch(
        APIGatewayResponse.model_induvidual
    ),
    "{0}/domainnames/(?P<domain_name>[^/]+)/?$": APIGatewayResponse.method_dispatch(
        APIGatewayResponse.domain_name_induvidual
    ),
    "{0}/domainnames/(?P<domain_name>[^/]+)/basepathmappings$": APIGatewayResponse.method_dispatch(
        APIGatewayResponse.base_path_mappings
    ),
    "{0}/domainnames/(?P<domain_name>[^/]+)/basepathmappings/(?P<base_path_mapping>[^/]+)$": APIGatewayResponse.method_dispatch(
        APIGatewayResponse.base_path_mapping_individual
    ),
    "{0}/usageplans/(?P<usage_plan_id>[^/]+)/?$": APIGatewayResponse.method_dispatch(
        APIGatewayResponse.usage_plan_individual
    ),
    "{0}/usageplans/(?P<usage_plan_id>[^/]+)/keys$": APIGatewayResponse.method_dispatch(
        APIGatewayResponse.usage_plan_keys
    ),
    "{0}/usageplans/(?P<usage_plan_id>[^/]+)/keys/(?P<api_key_id>[^/]+)/?$": APIGatewayResponse.method_dispatch(
        APIGatewayResponse.usage_plan_key_individual
    ),
    "{0}/restapis/(?P<function_id>[^/]+)/requestvalidators$": APIGatewayResponse.method_dispatch(
        APIGatewayResponse.request_validators
    ),
    "{0}/restapis/(?P<api_id>[^/]+)/requestvalidators/(?P<validator_id>[^/]+)/?$": APIGatewayResponse.method_dispatch(
        APIGatewayResponse.request_validator_individual
    ),
    "{0}/restapis/(?P<api_id>[^/]+)/gatewayresponses/?$": APIGatewayResponse.method_dispatch(
        APIGatewayResponse.gateway_responses
    ),
    "{0}/restapis/(?P<api_id>[^/]+)/gatewayresponses/(?P<response_type>[^/]+)/?$": APIGatewayResponse.method_dispatch(
        APIGatewayResponse.gateway_response
    ),
    "{0}/vpclinks$": APIGatewayResponse.method_dispatch(APIGatewayResponse.vpc_links),
    "{0}/vpclinks/(?P<vpclink_id>[^/]+)": APIGatewayResponse.method_dispatch(
        APIGatewayResponse.vpc_link
    ),
}

# Also manages the APIGatewayV2
url_paths.update(url_paths_v2)
