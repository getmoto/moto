.. _implementedservice_lambda:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

======
lambda
======

.. autoclass:: moto.awslambda.models.LambdaBackend

|start-h3| Implemented features for this service |end-h3|

- [ ] add_layer_version_permission
- [X] add_permission
- [X] create_alias
- [ ] create_code_signing_config
- [X] create_event_source_mapping
- [X] create_function
  
        The Code.ImageUri is not validated by default. Set environment variable MOTO_LAMBDA_STUB_ECR=false if you want to validate the image exists in our mocked ECR.
        

- [X] create_function_url_config
  
        The Qualifier-parameter is not yet implemented.
        Function URLs are not yet mocked, so invoking them will fail
        

- [X] delete_alias
- [ ] delete_code_signing_config
- [X] delete_event_source_mapping
- [X] delete_function
- [ ] delete_function_code_signing_config
- [X] delete_function_concurrency
- [X] delete_function_event_invoke_config
- [X] delete_function_url_config
  
        The Qualifier-parameter is not yet implemented
        

- [X] delete_layer_version
- [ ] delete_provisioned_concurrency_config
- [ ] get_account_settings
- [X] get_alias
- [ ] get_code_signing_config
- [X] get_event_source_mapping
- [X] get_function
- [X] get_function_code_signing_config
- [X] get_function_concurrency
- [ ] get_function_configuration
- [X] get_function_event_invoke_config
- [X] get_function_url_config
  
        The Qualifier-parameter is not yet implemented
        

- [X] get_layer_version
- [ ] get_layer_version_by_arn
- [ ] get_layer_version_policy
- [X] get_policy
- [ ] get_provisioned_concurrency_config
- [ ] get_runtime_management_config
- [X] invoke
  
        Invoking a Function with PackageType=Image is not yet supported.

        Invoking a Funcation against Lambda without docker now supports customised responses, the default being `Simple Lambda happy path OK`.
        You can use a dedicated API to override this, by configuring a queue of expected results.

        A request to `invoke` will take the first result from that queue.

        Configure this queue by making an HTTP request to `/moto-api/static/lambda-simple/response`. An example invocation looks like this:

        .. sourcecode:: python

            expected_results = {"results": ["test", "test 2"], "region": "us-east-1"}
            resp = requests.post(
                "http://motoapi.amazonaws.com/moto-api/static/lambda-simple/response",
                json=expected_results
            )
            assert resp.status_code == 201

            client = boto3.client("lambda", region_name="us-east-1")
            resp = client.invoke(...) # resp["Payload"].read().decode() == "test"
            resp = client.invoke(...) # resp["Payload"].read().decode() == "test2"
        

- [ ] invoke_async
- [ ] invoke_with_response_stream
- [X] list_aliases
- [ ] list_code_signing_configs
- [X] list_event_source_mappings
- [X] list_function_event_invoke_configs
- [ ] list_function_url_configs
- [X] list_functions
- [ ] list_functions_by_code_signing_config
- [X] list_layer_versions
- [X] list_layers
- [ ] list_provisioned_concurrency_configs
- [X] list_tags
- [X] list_versions_by_function
- [X] publish_layer_version
- [X] publish_version
- [ ] put_function_code_signing_config
- [X] put_function_concurrency
  Establish concurrency limit/reservations for a function

        Actual lambda restricts concurrency to 1000 (default) per region/account
        across all functions; we approximate that behavior by summing across all
        functions (hopefully all in the same account and region) and allowing the
        caller to simulate an increased quota.

        By default, no quota is enforced in order to preserve compatibility with
        existing code that assumes it can do as many things as it likes. To model
        actual AWS behavior, define the MOTO_LAMBDA_CONCURRENCY_QUOTA environment
        variable prior to testing.
        

- [X] put_function_event_invoke_config
- [ ] put_provisioned_concurrency_config
- [ ] put_runtime_management_config
- [ ] remove_layer_version_permission
- [X] remove_permission
- [X] tag_resource
- [X] untag_resource
- [X] update_alias
  
        The RevisionId parameter is not yet implemented
        

- [ ] update_code_signing_config
- [X] update_event_source_mapping
- [X] update_function_code
- [X] update_function_configuration
- [X] update_function_event_invoke_config
- [X] update_function_url_config
  
        The Qualifier-parameter is not yet implemented
        


