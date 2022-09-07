from .responses import LambdaResponse

url_bases = [r"https?://lambda\.(.+)\.amazonaws\.com"]

response = LambdaResponse()

url_paths = {
    r"{0}/(?P<api_version>[^/]+)/functions/?$": response.root,
    r"{0}/(?P<api_version>[^/]+)/functions/(?P<function_name>[\w_:%-]+)/?$": response.function,
    r"{0}/(?P<api_version>[^/]+)/functions/(?P<function_name>[\w_:%-]+)/aliases$": response.aliases,
    r"{0}/(?P<api_version>[^/]+)/functions/(?P<function_name>[\w_:%-]+)/aliases/(?P<alias_name>[\w_-]+)$": response.alias,
    r"{0}/(?P<api_version>[^/]+)/functions/(?P<function_name>[\w_:%-]+)/versions/?$": response.versions,
    r"{0}/(?P<api_version>[^/]+)/event-source-mappings/?$": response.event_source_mappings,
    r"{0}/(?P<api_version>[^/]+)/event-source-mappings/(?P<UUID>[\w_-]+)/?$": response.event_source_mapping,
    r"{0}/(?P<api_version>[^/]+)/functions/(?P<function_name>[\w_-]+)/invocations/?$": response.invoke,
    r"{0}/(?P<api_version>[^/]+)/functions/(?P<resource_arn>.+)/invocations/?$": response.invoke,
    r"{0}/(?P<api_version>[^/]+)/functions/(?P<function_name>[\w_:%-]+)/invoke-async/?$": response.invoke_async,
    r"{0}/(?P<api_version>[^/]+)/tags/(?P<resource_arn>.+)": response.tag,
    r"{0}/(?P<api_version>[^/]+)/functions/(?P<function_name>[\w_:%-]+)/policy/(?P<statement_id>[\w_-]+)$": response.policy,
    r"{0}/(?P<api_version>[^/]+)/functions/(?P<function_name>[\w_:%-]+)/policy/?$": response.policy,
    r"{0}/(?P<api_version>[^/]+)/functions/(?P<function_name>[\w_:%-]+)/configuration/?$": response.configuration,
    r"{0}/(?P<api_version>[^/]+)/functions/(?P<function_name>[\w_:%-]+)/code/?$": response.code,
    r"{0}/(?P<api_version>[^/]+)/functions/(?P<function_name>[\w_:%-]+)/code-signing-config$": response.code_signing_config,
    r"{0}/(?P<api_version>[^/]+)/functions/(?P<function_name>[\w_:%-]+)/concurrency/?$": response.function_concurrency,
    r"{0}/(?P<api_version>[^/]+)/functions/(?P<function_name>[\w_:%-]+)/url/?$": response.function_url_config,
    r"{0}/(?P<api_version>[^/]+)/layers/?$": response.list_layers,
    r"{0}/(?P<api_version>[^/]+)/layers/(?P<layer_name>[\w_-]+)/versions/?$": response.layers_versions,
    r"{0}/(?P<api_version>[^/]+)/layers/(?P<layer_name>[\w_-]+)/versions/(?P<layer_version>[\w_-]+)$": response.layers_version,
}
