.. _implementedservice_appconfig:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

=========
appconfig
=========

.. autoclass:: moto.appconfig.models.AppConfigBackend

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_appconfig
            def test_appconfig_behaviour:
                boto3.client("appconfig")
                ...



|start-h3| Implemented features for this service |end-h3|

- [X] create_application
- [X] create_configuration_profile
- [ ] create_deployment_strategy
- [ ] create_environment
- [ ] create_extension
- [ ] create_extension_association
- [X] create_hosted_configuration_version
  
        The LatestVersionNumber-parameter is not yet implemented
        

- [X] delete_application
- [X] delete_configuration_profile
- [ ] delete_deployment_strategy
- [ ] delete_environment
- [ ] delete_extension
- [ ] delete_extension_association
- [X] delete_hosted_configuration_version
- [X] get_application
- [ ] get_configuration
- [X] get_configuration_profile
- [ ] get_deployment
- [ ] get_deployment_strategy
- [ ] get_environment
- [ ] get_extension
- [ ] get_extension_association
- [X] get_hosted_configuration_version
- [ ] list_applications
- [X] list_configuration_profiles
- [ ] list_deployment_strategies
- [ ] list_deployments
- [ ] list_environments
- [ ] list_extension_associations
- [ ] list_extensions
- [ ] list_hosted_configuration_versions
- [X] list_tags_for_resource
- [ ] start_deployment
- [ ] stop_deployment
- [X] tag_resource
- [X] untag_resource
- [X] update_application
- [X] update_configuration_profile
- [ ] update_deployment_strategy
- [ ] update_environment
- [ ] update_extension
- [ ] update_extension_association
- [ ] validate_configuration

