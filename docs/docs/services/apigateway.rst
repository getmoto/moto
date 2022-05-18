.. _implementedservice_apigateway:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

==========
apigateway
==========

.. autoclass:: moto.apigateway.models.APIGatewayBackend

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_apigateway
            def test_apigateway_behaviour:
                boto3.client("apigateway")
                ...



|start-h3| Implemented features for this service |end-h3|

- [X] create_api_key
- [X] create_authorizer
- [X] create_base_path_mapping
- [X] create_deployment
- [ ] create_documentation_part
- [ ] create_documentation_version
- [X] create_domain_name
- [X] create_model
- [X] create_request_validator
- [X] create_resource
- [X] create_rest_api
- [X] create_stage
- [X] create_usage_plan
- [X] create_usage_plan_key
- [X] create_vpc_link
- [X] delete_api_key
- [X] delete_authorizer
- [X] delete_base_path_mapping
- [ ] delete_client_certificate
- [X] delete_deployment
- [ ] delete_documentation_part
- [ ] delete_documentation_version
- [X] delete_domain_name
- [X] delete_gateway_response
- [X] delete_integration
- [X] delete_integration_response
- [X] delete_method
- [X] delete_method_response
- [ ] delete_model
- [X] delete_request_validator
- [X] delete_resource
- [X] delete_rest_api
- [X] delete_stage
- [X] delete_usage_plan
- [X] delete_usage_plan_key
- [X] delete_vpc_link
- [ ] flush_stage_authorizers_cache
- [ ] flush_stage_cache
- [ ] generate_client_certificate
- [ ] get_account
- [X] get_api_key
- [X] get_api_keys
- [X] get_authorizer
- [X] get_authorizers
- [X] get_base_path_mapping
- [X] get_base_path_mappings
- [ ] get_client_certificate
- [ ] get_client_certificates
- [X] get_deployment
- [X] get_deployments
- [ ] get_documentation_part
- [ ] get_documentation_parts
- [ ] get_documentation_version
- [ ] get_documentation_versions
- [X] get_domain_name
- [X] get_domain_names
- [ ] get_export
- [X] get_gateway_response
- [X] get_gateway_responses
  
        Pagination is not yet implemented
        

- [X] get_integration
- [X] get_integration_response
- [X] get_method
- [X] get_method_response
- [X] get_model
- [ ] get_model_template
- [X] get_models
- [X] get_request_validator
- [X] get_request_validators
- [X] get_resource
- [X] get_resources
- [X] get_rest_api
- [ ] get_rest_apis
- [ ] get_sdk
- [ ] get_sdk_type
- [ ] get_sdk_types
- [X] get_stage
- [X] get_stages
- [ ] get_tags
- [ ] get_usage
- [X] get_usage_plan
- [X] get_usage_plan_key
- [X] get_usage_plan_keys
- [X] get_usage_plans
- [X] get_vpc_link
- [X] get_vpc_links
  
        Pagination has not yet been implemented
        

- [ ] import_api_keys
- [ ] import_documentation_parts
- [X] import_rest_api
  
        Only a subset of the OpenAPI spec 3.x is currently implemented.
        

- [X] put_gateway_response
- [X] put_integration
- [X] put_integration_response
- [X] put_method
- [X] put_method_response
- [X] put_rest_api
  
        Only a subset of the OpenAPI spec 3.x is currently implemented.
        

- [ ] tag_resource
- [ ] test_invoke_authorizer
- [ ] test_invoke_method
- [ ] untag_resource
- [ ] update_account
- [X] update_api_key
- [X] update_authorizer
- [X] update_base_path_mapping
- [ ] update_client_certificate
- [ ] update_deployment
- [ ] update_documentation_part
- [ ] update_documentation_version
- [X] update_domain_name
- [ ] update_gateway_response
- [ ] update_integration
- [ ] update_integration_response
- [X] update_method
- [X] update_method_response
- [ ] update_model
- [X] update_request_validator
- [ ] update_resource
- [X] update_rest_api
- [X] update_stage
- [ ] update_usage
- [X] update_usage_plan
- [ ] update_vpc_link

