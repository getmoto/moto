.. _implementedservice_resource-groups:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

===============
resource-groups
===============



|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_resourcegroups
            def test_resource-groups_behaviour:
                boto3.client("resource-groups")
                ...



|start-h3| Implemented features for this service |end-h3|

- [X] create_group
- [X] delete_group
- [X] get_group
- [X] get_group_configuration
- [ ] get_group_query
- [X] get_tags
- [ ] group_resources
- [ ] list_group_resources
- [X] list_groups
- [X] put_group_configuration
- [ ] search_resources
- [X] tag
- [ ] ungroup_resources
- [X] untag
- [X] update_group
- [X] update_group_query

