.. _implementedservice_inspector2:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

==========
inspector2
==========

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_inspector2
            def test_inspector2_behaviour:
                boto3.client("inspector2")
                ...



|start-h3| Implemented features for this service |end-h3|

- [X] associate_member
- [X] batch_get_account_status
- [ ] batch_get_code_snippet
- [ ] batch_get_finding_details
- [ ] batch_get_free_trial_info
- [ ] batch_get_member_ec2_deep_inspection_status
- [ ] batch_update_member_ec2_deep_inspection_status
- [ ] cancel_findings_report
- [ ] cancel_sbom_export
- [X] create_filter
- [ ] create_findings_report
- [ ] create_sbom_export
- [X] delete_filter
- [X] describe_organization_configuration
- [X] disable
- [X] disable_delegated_admin_account
- [X] disassociate_member
- [X] enable
- [X] enable_delegated_admin_account
- [ ] get_configuration
- [ ] get_delegated_admin_account
- [ ] get_ec2_deep_inspection_configuration
- [ ] get_encryption_key
- [ ] get_findings_report_status
- [X] get_member
- [ ] get_sbom_export
- [ ] list_account_permissions
- [ ] list_coverage
- [ ] list_coverage_statistics
- [X] list_delegated_admin_accounts
- [X] list_filters
  
        Pagination is not yet implemented
        

- [ ] list_finding_aggregations
- [X] list_findings
  
        This call will always return 0 findings by default.

        You can use a dedicated API to override this, by configuring a queue of expected results.

        A request to `list_findings` will take the first result from that queue, and assign it to the provided arguments. Subsequent calls using the same arguments will return the same result. Other requests using a different SQL-query will take the next result from the queue, or return an empty result if the queue is empty.

        Configure this queue by making an HTTP request to `/moto-api/static/inspector2/findings-results`. An example invocation looks like this:

        .. sourcecode:: python

            findings = {
                "results": [
                    [{
                        "awsAccountId": "111122223333",
                        "codeVulnerabilityDetails": {"cwes": ["a"], "detectorId": ".."},
                    }],
                    # .. other findings as required
                ],
                "account_id": "123456789012",  # This is the default - can be omitted
                "region": "us-east-1",  # This is the default - can be omitted
            }
            resp = requests.post(
                "http://motoapi.amazonaws.com:5000/moto-api/static/inspector2/findings-results",
                json=findings,
            )

            inspector2 = boto3.client("inspector2", region_name="us-east-1")
            findings = inspector2.list_findings()["findings"]

        

- [X] list_members
- [X] list_tags_for_resource
- [ ] list_usage_totals
- [ ] reset_encryption_key
- [ ] search_vulnerabilities
- [X] tag_resource
- [X] untag_resource
- [ ] update_configuration
- [ ] update_ec2_deep_inspection_configuration
- [ ] update_encryption_key
- [ ] update_filter
- [ ] update_org_ec2_deep_inspection_configuration
- [X] update_organization_configuration

