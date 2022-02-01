.. _implementedservice_redshift-data:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

========
redshift-data
========

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_redshiftdata
            def test_redshift_behaviour:
                boto3.client("redshift-data")
                ...



|start-h3| Implemented features for this service |end-h3|

- [ ] batch_execute_statement
- [ ] can_paginate
- [X] cancel_statement
- [X] describe_statement
- [ ] describe_table
- [X] execute_statement
- [ ] get_paginator
- [X] get_statement_result
- [ ] get_waiter
- [ ] list_databases
- [ ] list_schemas
- [ ] list_statements
- [ ] list_tables
