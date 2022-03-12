.. _implementedservice_support:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

=======
support
=======

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_support
            def test_support_behaviour:
                boto3.client("support")
                ...



|start-h3| Implemented features for this service |end-h3|

- [ ] add_attachments_to_set
- [ ] add_communication_to_case
- [X] create_case
  
        The IssueType-parameter is not yet implemented
        

- [ ] describe_attachment
- [X] describe_cases
  
        The following parameters have not yet been implemented:
        DisplayID, AfterTime, BeforeTime, MaxResults, Language
        

- [ ] describe_communications
- [ ] describe_services
- [ ] describe_severity_levels
- [ ] describe_trusted_advisor_check_refresh_statuses
- [ ] describe_trusted_advisor_check_result
- [ ] describe_trusted_advisor_check_summaries
- [X] describe_trusted_advisor_checks
  
        The Language-parameter is not yet implemented
        

- [X] refresh_trusted_advisor_check
- [X] resolve_case

