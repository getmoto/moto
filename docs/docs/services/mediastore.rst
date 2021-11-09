.. _implementedservice_mediastore:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

==========
mediastore
==========



|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_mediastore
            def test_mediastore_behaviour:
                boto3.client("mediastore")
                ...



|start-h3| Implemented features for this service |end-h3|

- [X] create_container
- [X] delete_container
- [ ] delete_container_policy
- [ ] delete_cors_policy
- [ ] delete_lifecycle_policy
- [ ] delete_metric_policy
- [X] describe_container
- [X] get_container_policy
- [ ] get_cors_policy
- [X] get_lifecycle_policy
- [X] get_metric_policy
- [X] list_containers
- [X] list_tags_for_resource
- [X] put_container_policy
- [ ] put_cors_policy
- [X] put_lifecycle_policy
- [X] put_metric_policy
- [ ] start_access_logging
- [ ] stop_access_logging
- [ ] tag_resource
- [ ] untag_resource

