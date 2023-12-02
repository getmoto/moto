.. _implementedservice_secretsmanager:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

==============
secretsmanager
==============

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_secretsmanager
            def test_secretsmanager_behaviour:
                boto3.client("secretsmanager")
                ...



|start-h3| Implemented features for this service |end-h3|

- [ ] batch_get_secret_value
- [X] cancel_rotate_secret
- [X] create_secret
- [X] delete_resource_policy
- [X] delete_secret
- [X] describe_secret
- [X] get_random_password
- [X] get_resource_policy
- [X] get_secret_value
- [X] list_secret_version_ids
- [X] list_secrets
- [X] put_resource_policy
  
        The BlockPublicPolicy-parameter is not yet implemented
        

- [X] put_secret_value
- [ ] remove_regions_from_replication
- [ ] replicate_secret_to_regions
- [X] restore_secret
- [X] rotate_secret
- [ ] stop_replication_to_replica
- [X] tag_resource
- [X] untag_resource
- [X] update_secret
- [X] update_secret_version_stage
- [ ] validate_resource_policy

