from .responses import LambdaResponse

url_bases = [r"https?://lambda\.(.+)\.amazonaws\.com"]


url_paths = {
    r"{0}/(?P<api_version>[^/]+)/functions$": LambdaResponse.method_dispatch(
        LambdaResponse.root
    ),
    r"{0}/(?P<api_version>[^/]+)/functions/$": LambdaResponse.method_dispatch(
        LambdaResponse.root
    ),
    r"{0}/(?P<api_version>[^/]+)/functions/(?P<function_name>[\w_:%-]+)/?$": LambdaResponse.method_dispatch(
        LambdaResponse.function
    ),
    r"{0}/(?P<api_version>[^/]+)/functions/(?P<function_name>[\w_:%-]+)/aliases$": LambdaResponse.method_dispatch(
        LambdaResponse.aliases
    ),
    r"{0}/(?P<api_version>[^/]+)/functions/(?P<function_name>[\w_:%-]+)/aliases/(?P<alias_name>[\w_-]+)$": LambdaResponse.method_dispatch(
        LambdaResponse.alias
    ),
    r"{0}/(?P<api_version>[^/]+)/functions/(?P<function_name>[\w_:%-]+)/versions/?$": LambdaResponse.method_dispatch(
        LambdaResponse.versions
    ),
    r"{0}/(?P<api_version>[^/]+)/event-source-mappings/$": LambdaResponse.method_dispatch(
        LambdaResponse.event_source_mappings
    ),
    r"{0}/(?P<api_version>[^/]+)/event-source-mappings/(?P<UUID>[\w_-]+)/?$": LambdaResponse.method_dispatch(
        LambdaResponse.event_source_mapping
    ),
    r"{0}/(?P<api_version>[^/]+)/functions/(?P<function_name>[\w_-]+)/invocations/?$": LambdaResponse.method_dispatch(
        LambdaResponse.invoke
    ),
    r"{0}/(?P<api_version>[^/]+)/functions/(?P<resource_arn>.+)/invocations/?$": LambdaResponse.method_dispatch(
        LambdaResponse.invoke
    ),
    r"{0}/(?P<api_version>[^/]+)/functions/(?P<function_name>[\w_:%-]+)/invoke-async$": LambdaResponse.method_dispatch(
        LambdaResponse.invoke_async
    ),
    r"{0}/(?P<api_version>[^/]+)/functions/(?P<function_name>[\w_:%-]+)/invoke-async/$": LambdaResponse.method_dispatch(
        LambdaResponse.invoke_async
    ),
    r"{0}/(?P<api_version>[^/]+)/tags/(?P<resource_arn>.+)": LambdaResponse.method_dispatch(
        LambdaResponse.tag
    ),
    r"{0}/(?P<api_version>[^/]+)/functions/(?P<function_name>[\w_:%-]+)/policy/(?P<statement_id>[\w_-]+)$": LambdaResponse.method_dispatch(
        LambdaResponse.policy
    ),
    r"{0}/(?P<api_version>[^/]+)/functions/(?P<function_name>[\w_:%-]+)/policy/?$": LambdaResponse.method_dispatch(
        LambdaResponse.policy
    ),
    r"{0}/(?P<api_version>[^/]+)/functions/(?P<function_name>[\w_:%-]+)/configuration/?$": LambdaResponse.method_dispatch(
        LambdaResponse.configuration
    ),
    r"{0}/(?P<api_version>[^/]+)/functions/(?P<function_name>[\w_:%-]+)/code/?$": LambdaResponse.method_dispatch(
        LambdaResponse.code
    ),
    r"{0}/(?P<api_version>[^/]+)/functions/(?P<function_name>[\w_:%-]+)/code-signing-config$": LambdaResponse.method_dispatch(
        LambdaResponse.code_signing_config
    ),
    r"{0}/(?P<api_version>[^/]+)/functions/(?P<function_name>[\w_:%-]+)/concurrency/?$": LambdaResponse.method_dispatch(
        LambdaResponse.function_concurrency
    ),
    r"{0}/(?P<api_version>[^/]+)/functions/(?P<function_name>[\w_:%-]+)/url/?$": LambdaResponse.method_dispatch(
        LambdaResponse.function_url_config
    ),
    r"{0}/(?P<api_version>[^/]+)/layers$": LambdaResponse.method_dispatch(
        LambdaResponse.list_layers
    ),
    r"{0}/(?P<api_version>[^/]+)/layers/$": LambdaResponse.method_dispatch(
        LambdaResponse.list_layers
    ),
    r"{0}/(?P<api_version>[^/]+)/layers/(?P<layer_name>.+)/versions$": LambdaResponse.method_dispatch(
        LambdaResponse.layers_versions
    ),
    r"{0}/(?P<api_version>[^/]+)/layers/(?P<layer_name>.+)/versions/$": LambdaResponse.method_dispatch(
        LambdaResponse.layers_versions
    ),
    r"{0}/(?P<api_version>[^/]+)/layers/(?P<layer_name>.+)/versions/(?P<layer_version>[\w_-]+)$": LambdaResponse.method_dispatch(
        LambdaResponse.layers_version
    ),
}
