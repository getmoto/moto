.. _implementedservice_appsync:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

=======
appsync
=======

.. autoclass:: moto.appsync.models.AppSyncBackend

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_appsync
            def test_appsync_behaviour:
                boto3.client("appsync")
                ...



|start-h3| Implemented features for this service |end-h3|

- [ ] associate_api
- [ ] associate_merged_graphql_api
- [ ] associate_source_graphql_api
- [ ] create_api_cache
- [X] create_api_key
- [ ] create_data_source
- [ ] create_domain_name
- [ ] create_function
- [X] create_graphql_api
- [ ] create_resolver
- [ ] create_type
- [ ] delete_api_cache
- [X] delete_api_key
- [ ] delete_data_source
- [ ] delete_domain_name
- [ ] delete_function
- [X] delete_graphql_api
- [ ] delete_resolver
- [ ] delete_type
- [ ] disassociate_api
- [ ] disassociate_merged_graphql_api
- [ ] disassociate_source_graphql_api
- [ ] evaluate_code
- [ ] evaluate_mapping_template
- [ ] flush_api_cache
- [ ] get_api_association
- [ ] get_api_cache
- [ ] get_data_source
- [ ] get_domain_name
- [ ] get_function
- [X] get_graphql_api
- [ ] get_introspection_schema
- [ ] get_resolver
- [X] get_schema_creation_status
- [ ] get_source_api_association
- [X] get_type
- [X] list_api_keys
  
        Pagination or the maxResults-parameter have not yet been implemented.
        

- [ ] list_data_sources
- [ ] list_domain_names
- [ ] list_functions
- [X] list_graphql_apis
  
        Pagination or the maxResults-parameter have not yet been implemented.
        

- [ ] list_resolvers
- [ ] list_resolvers_by_function
- [ ] list_source_api_associations
- [X] list_tags_for_resource
- [ ] list_types
- [ ] list_types_by_association
- [X] start_schema_creation
- [ ] start_schema_merge
- [X] tag_resource
- [X] untag_resource
- [ ] update_api_cache
- [X] update_api_key
- [ ] update_data_source
- [ ] update_domain_name
- [ ] update_function
- [X] update_graphql_api
- [ ] update_resolver
- [ ] update_source_api_association
- [ ] update_type

