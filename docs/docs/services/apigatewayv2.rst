.. _implementedservice_apigatewayv2:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

============
apigatewayv2
============

.. autoclass:: moto.apigatewayv2.models.ApiGatewayV2Backend

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_apigatewayv2
            def test_apigatewayv2_behaviour:
                boto3.client("apigatewayv2")
                ...



|start-h3| Implemented features for this service |end-h3|

- [X] create_api
  
        The following parameters are not yet implemented:
        CredentialsArn, RouteKey, Tags, Target
        

- [X] create_api_mapping
- [X] create_authorizer
- [ ] create_deployment
- [X] create_domain_name
- [X] create_integration
- [X] create_integration_response
- [X] create_model
- [X] create_route
- [X] create_route_response
  
        The following parameters are not yet implemented: ResponseModels, ResponseParameters
        

- [X] create_stage
- [X] create_vpc_link
- [ ] delete_access_log_settings
- [X] delete_api
- [X] delete_api_mapping
- [X] delete_authorizer
- [X] delete_cors_configuration
- [ ] delete_deployment
- [X] delete_domain_name
- [X] delete_integration
- [X] delete_integration_response
- [X] delete_model
- [X] delete_route
- [X] delete_route_request_parameter
- [X] delete_route_response
- [ ] delete_route_settings
- [X] delete_stage
- [X] delete_vpc_link
- [ ] export_api
- [X] get_api
- [X] get_api_mapping
- [X] get_api_mappings
- [X] get_apis
  
        Pagination is not yet implemented
        

- [X] get_authorizer
- [ ] get_authorizers
- [ ] get_deployment
- [ ] get_deployments
- [X] get_domain_name
- [X] get_domain_names
  
        Pagination is not yet implemented
        

- [X] get_integration
- [X] get_integration_response
- [X] get_integration_responses
- [X] get_integrations
  
        Pagination is not yet implemented
        

- [X] get_model
- [ ] get_model_template
- [ ] get_models
- [X] get_route
- [X] get_route_response
- [ ] get_route_responses
- [X] get_routes
  
        Pagination is not yet implemented
        

- [X] get_stage
- [X] get_stages
- [X] get_tags
- [X] get_vpc_link
- [X] get_vpc_links
- [ ] import_api
- [X] reimport_api
  
        Only YAML is supported at the moment. Full OpenAPI-support is not guaranteed. Only limited validation is implemented
        

- [ ] reset_authorizers_cache
- [X] tag_resource
- [X] untag_resource
- [X] update_api
  
        The following parameters have not yet been implemented: CredentialsArn, RouteKey, Target
        

- [ ] update_api_mapping
- [X] update_authorizer
- [ ] update_deployment
- [ ] update_domain_name
- [X] update_integration
- [X] update_integration_response
- [X] update_model
- [X] update_route
- [ ] update_route_response
- [ ] update_stage
- [X] update_vpc_link

