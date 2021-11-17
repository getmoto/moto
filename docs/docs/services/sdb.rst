.. _implementedservice_sdb:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

===
sdb
===

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_sdb
            def test_sdb_behaviour:
                boto3.client("sdb")
                ...



|start-h3| Implemented features for this service |end-h3|

- [ ] batch_delete_attributes
- [ ] batch_put_attributes
- [X] create_domain
- [ ] delete_attributes
- [X] delete_domain
- [ ] domain_metadata
- [X] get_attributes
  
        Behaviour for the consistent_read-attribute is not yet implemented
        

- [X] list_domains
  
        The `max_number_of_domains` and `next_token` parameter have not been implemented yet - we simply return all domains.
        

- [X] put_attributes
  
        Behaviour for the expected-attribute is not yet implemented.
        

- [ ] select

