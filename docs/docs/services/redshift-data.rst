.. _implementedservice_redshift-data:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

=============
redshift-data
=============

|start-h3| Implemented features for this service |end-h3|

- [ ] batch_execute_statement
- [X] cancel_statement
- [X] describe_statement
- [ ] describe_table
- [X] execute_statement
  
        Runs an SQL statement
        Validation of parameters is very limited because there is no redshift integration
        

- [X] get_statement_result
  
        Return static statement result
        StatementResult is the result of the SQL query "sql" passed as parameter when calling "execute_statement"
        As such, it cannot be mocked
        

- [ ] get_statement_result_v2
- [ ] list_databases
- [ ] list_schemas
- [ ] list_statements
- [ ] list_tables

