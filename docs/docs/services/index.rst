.. _implemented_services:


====================
Implemented Services
====================

Please see a list of all currently supported services. Each service will have a list of the endpoints that are implemented.
Each service will also have an example on how to mock an individual service.

Note that you can mock multiple services at the same time:

.. sourcecode:: python

    @mock_s3
    @mock_sqs
    def test_both_s3_and_sqs():
        ...


.. sourcecode:: python

    @mock_all()
    def test_all_supported_services_at_the_same_time():
        ...


.. toctree::
    :titlesonly:
    :maxdepth: 1
    :glob:

    *
