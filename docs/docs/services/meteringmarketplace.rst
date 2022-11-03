.. _implementedservice_meteringmarketplace:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

===================
meteringmarketplace
===================

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_meteringmarketplace
            def test_meteringmarketplace_behaviour:
                boto3.client("meteringmarketplace")
                ...



|start-h3| Implemented features for this service |end-h3|

- [X] batch_meter_usage
- [ ] meter_usage
- [ ] register_usage
- [ ] resolve_customer

