"""apigatewayv2 base URL and path."""
from .responses import ApiGatewayV2Response

url_bases = [
    r"https?://apigateway\.(.+)\.amazonaws\.com",
]


url_paths = {
    "{0}/v2/apis$": ApiGatewayV2Response.method_dispatch(ApiGatewayV2Response.apis),
    "{0}/v2/apis/(?P<api_id>[^/]+)$": ApiGatewayV2Response.method_dispatch(
        ApiGatewayV2Response.api
    ),
    "{0}/v2/apis/(?P<api_id>[^/]+)/authorizers$": ApiGatewayV2Response.method_dispatch(
        ApiGatewayV2Response.authorizers
    ),
    "{0}/v2/apis/(?P<api_id>[^/]+)/authorizers/(?P<authorizer_id>[^/]+)$": ApiGatewayV2Response.method_dispatch(
        ApiGatewayV2Response.authorizer
    ),
    "{0}/v2/apis/(?P<api_id>[^/]+)/cors$": ApiGatewayV2Response.method_dispatch(
        ApiGatewayV2Response.cors
    ),
    "{0}/v2/apis/(?P<api_id>[^/]+)/integrations$": ApiGatewayV2Response.method_dispatch(
        ApiGatewayV2Response.integrations
    ),
    "{0}/v2/apis/(?P<api_id>[^/]+)/integrations/(?P<integration_id>[^/]+)$": ApiGatewayV2Response.method_dispatch(
        ApiGatewayV2Response.integration
    ),
    "{0}/v2/apis/(?P<api_id>[^/]+)/integrations/(?P<integration_id>[^/]+)/integrationresponses$": ApiGatewayV2Response.method_dispatch(
        ApiGatewayV2Response.integration_responses
    ),
    "{0}/v2/apis/(?P<api_id>[^/]+)/integrations/(?P<integration_id>[^/]+)/integrationresponses/(?P<integration_response_id>[^/]+)$": ApiGatewayV2Response.method_dispatch(
        ApiGatewayV2Response.integration_response
    ),
    "{0}/v2/apis/(?P<api_id>[^/]+)/models$": ApiGatewayV2Response.method_dispatch(
        ApiGatewayV2Response.models
    ),
    "{0}/v2/apis/(?P<api_id>[^/]+)/models/(?P<model_id>[^/]+)$": ApiGatewayV2Response.method_dispatch(
        ApiGatewayV2Response.model
    ),
    "{0}/v2/apis/(?P<api_id>[^/]+)/routes$": ApiGatewayV2Response.method_dispatch(
        ApiGatewayV2Response.routes
    ),
    "{0}/v2/apis/(?P<api_id>[^/]+)/routes/(?P<route_id>[^/]+)$": ApiGatewayV2Response.method_dispatch(
        ApiGatewayV2Response.route
    ),
    "{0}/v2/apis/(?P<api_id>[^/]+)/routes/(?P<route_id>[^/]+)/routeresponses$": ApiGatewayV2Response.method_dispatch(
        ApiGatewayV2Response.route_responses
    ),
    "{0}/v2/apis/(?P<api_id>[^/]+)/routes/(?P<route_id>[^/]+)/routeresponses/(?P<route_response_id>[^/]+)$": ApiGatewayV2Response.method_dispatch(
        ApiGatewayV2Response.route_response
    ),
    "{0}/v2/apis/(?P<api_id>[^/]+)/routes/(?P<route_id>[^/]+)/requestparameters/(?P<request_parameter>[^/]+)$": ApiGatewayV2Response.method_dispatch(
        ApiGatewayV2Response.route_request_parameter
    ),
    "{0}/v2/apis/(?P<api_id>[^/]+)/stages$": ApiGatewayV2Response.method_dispatch(
        ApiGatewayV2Response.stages
    ),
    "{0}/v2/apis/(?P<api_id>[^/]+)/stages/(?P<stage_name>[^/]+)$": ApiGatewayV2Response.method_dispatch(
        ApiGatewayV2Response.stage
    ),
    "{0}/v2/tags/(?P<resource_arn>[^/]+)$": ApiGatewayV2Response.method_dispatch(
        ApiGatewayV2Response.tags
    ),
    "{0}/v2/tags/(?P<resource_arn_pt1>[^/]+)/apis/(?P<resource_arn_pt2>[^/]+)$": ApiGatewayV2Response.method_dispatch(
        ApiGatewayV2Response.tags
    ),
    "{0}/v2/tags/(?P<resource_arn_pt1>[^/]+)/vpclinks/(?P<resource_arn_pt2>[^/]+)$": ApiGatewayV2Response.method_dispatch(
        ApiGatewayV2Response.tags
    ),
    "{0}/v2/vpclinks$": ApiGatewayV2Response.method_dispatch(
        ApiGatewayV2Response.vpc_links
    ),
    "{0}/v2/vpclinks/(?P<vpc_link_id>[^/]+)$": ApiGatewayV2Response.method_dispatch(
        ApiGatewayV2Response.vpc_link
    ),
    "{0}/v2/domainnames$": ApiGatewayV2Response.method_dispatch(
        ApiGatewayV2Response.domain_names
    ),
    "{0}/v2/domainnames/(?P<domain_name>[^/]+)$": ApiGatewayV2Response.method_dispatch(
        ApiGatewayV2Response.domain_name
    ),
    "{0}/v2/domainnames/(?P<domain_name>[^/]+)/apimappings$": ApiGatewayV2Response.method_dispatch(
        ApiGatewayV2Response.api_mappings
    ),
    "{0}/v2/domainnames/(?P<domain_name>[^/]+)/apimappings/(?P<api_mapping_id>[^/]+)$": ApiGatewayV2Response.method_dispatch(
        ApiGatewayV2Response.api_mapping
    ),
}
