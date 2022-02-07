"""apigatewayv2 base URL and path."""
from .responses import ApiGatewayV2Response

url_bases = [
    r"https?://apigateway\.(.+)\.amazonaws\.com",
]


response_v2 = ApiGatewayV2Response()


url_paths = {
    "{0}/v2/apis$": response_v2.apis,
    "{0}/v2/apis/(?P<api_id>[^/]+)$": response_v2.api,
    "{0}/v2/apis/(?P<api_id>[^/]+)/authorizers$": response_v2.authorizers,
    "{0}/v2/apis/(?P<api_id>[^/]+)/authorizers/(?P<authorizer_id>[^/]+)$": response_v2.authorizer,
    "{0}/v2/apis/(?P<api_id>[^/]+)/cors$": response_v2.cors,
    "{0}/v2/apis/(?P<api_id>[^/]+)/integrations$": response_v2.integrations,
    "{0}/v2/apis/(?P<api_id>[^/]+)/integrations/(?P<integration_id>[^/]+)$": response_v2.integration,
    "{0}/v2/apis/(?P<api_id>[^/]+)/integrations/(?P<integration_id>[^/]+)/integrationresponses$": response_v2.integration_responses,
    "{0}/v2/apis/(?P<api_id>[^/]+)/integrations/(?P<integration_id>[^/]+)/integrationresponses/(?P<integration_response_id>[^/]+)$": response_v2.integration_response,
    "{0}/v2/apis/(?P<api_id>[^/]+)/models$": response_v2.models,
    "{0}/v2/apis/(?P<api_id>[^/]+)/models/(?P<model_id>[^/]+)$": response_v2.model,
    "{0}/v2/apis/(?P<api_id>[^/]+)/routes$": response_v2.routes,
    "{0}/v2/apis/(?P<api_id>[^/]+)/routes/(?P<route_id>[^/]+)$": response_v2.route,
    "{0}/v2/apis/(?P<api_id>[^/]+)/routes/(?P<route_id>[^/]+)/routeresponses$": response_v2.route_responses,
    "{0}/v2/apis/(?P<api_id>[^/]+)/routes/(?P<route_id>[^/]+)/routeresponses/(?P<route_response_id>[^/]+)$": response_v2.route_response,
    "{0}/v2/apis/(?P<api_id>[^/]+)/routes/(?P<route_id>[^/]+)/requestparameters/(?P<request_parameter>[^/]+)$": response_v2.route_request_parameter,
    "{0}/v2/tags/(?P<resource_arn>.+)$": response_v2.tags,
    "{0}/v2/vpclinks$": response_v2.vpc_links,
    "{0}/v2/vpclinks/(?P<vpc_link_id>[^/]+)$": response_v2.vpc_link,
}
